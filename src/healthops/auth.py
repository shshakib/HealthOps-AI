"""Local accounts and revocable server-side sessions for the synthetic-data workspace."""

import argparse
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

COOKIE = "healthops_session"
SESSION_SECONDS = 8 * 60 * 60
Role = Literal["viewer", "reviewer", "admin"]


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(pattern=r"^[a-zA-Z0-9_.-]{3,64}$")
    password: str = Field(min_length=1, max_length=128)


class NewUser(Credentials):
    password: str = Field(min_length=15, max_length=128)
    role: Role = "viewer"


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role
    active: bool
    password: str | None = Field(default=None, min_length=15, max_length=128)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=15, max_length=128)


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=2**17, r=8, p=1, maxmem=256 * 1024 * 1024
    ).hex()
    return f"scrypt${salt}${digest}"


def password_matches(password: str, encoded: str) -> bool:
    return hmac.compare_digest(password_hash(password, encoded.split("$")[1]), encoded)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS auth_users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    username TEXT NOT NULL, address TEXT NOT NULL, occurred REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_events (
                    id INTEGER PRIMARY KEY, occurred REAL NOT NULL, actor TEXT,
                    action TEXT NOT NULL, target TEXT
                );
            """)
        # Same work for an unknown username, without retaining a usable credential.
        self.dummy_hash = password_hash(secrets.token_urlsafe(32))

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def event(conn, actor, action, target=None):
        conn.execute(
            "INSERT INTO auth_events(occurred, actor, action, target) VALUES (?, ?, ?, ?)",
            (time.time(), actor, action, target),
        )

    def users(self):
        with closing(self.connect()) as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT id, username, role, active FROM auth_users ORDER BY username"
                )
            ]

    def create_user(self, user: NewUser, actor=None, bootstrap=False):
        encoded = password_hash(user.password)
        identifier = str(uuid4())
        with closing(self.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            if bootstrap and conn.execute("SELECT 1 FROM auth_users LIMIT 1").fetchone():
                raise HTTPException(
                    409, "Accounts already exist; use administrator user management."
                )
            try:
                conn.execute(
                    "INSERT INTO auth_users VALUES (?, ?, ?, ?, 1)",
                    (identifier, user.username.lower(), encoded, user.role),
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, "Username already exists.") from exc
            self.event(conn, actor, "bootstrap_admin" if bootstrap else "user_created", identifier)
        return {
            "id": identifier,
            "username": user.username.lower(),
            "role": user.role,
            "active": True,
        }

    def login(self, credentials: Credentials, address: str):
        username = credentials.username.lower()
        now = time.time()
        with closing(self.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM auth_attempts WHERE occurred < ?", (now - 900,))
            count = conn.execute(
                "SELECT COUNT(*) FROM auth_attempts WHERE username = ?", (username,)
            ).fetchone()[0]
            ip_count = conn.execute(
                "SELECT COUNT(*) FROM auth_attempts WHERE address = ?", (address,)
            ).fetchone()[0]
            if count >= 5 or ip_count >= 30:
                raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
            conn.execute("INSERT INTO auth_attempts VALUES (?, ?, ?)", (username, address, now))
            user = conn.execute(
                "SELECT * FROM auth_users WHERE username = ?", (username,)
            ).fetchone()
        valid = password_matches(
            credentials.password, user["password"] if user else self.dummy_hash
        )
        with closing(self.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            # Recheck after hashing so a concurrent disable/reset cannot issue a session.
            current = conn.execute(
                "SELECT * FROM auth_users WHERE username = ?", (username,)
            ).fetchone()
            if (
                not valid
                or not current
                or not current["active"]
                or current["password"] != user["password"]
            ):
                self.event(conn, None, "login_failed")
                error = True
            else:
                error = False
                token = secrets.token_urlsafe(32)
                conn.execute("DELETE FROM auth_sessions WHERE expires <= ?", (now,))
                conn.execute("DELETE FROM auth_attempts WHERE username = ?", (username,))
                conn.execute(
                    "INSERT INTO auth_sessions VALUES (?, ?, ?)",
                    (token_hash(token), current["id"], now + SESSION_SECONDS),
                )
                self.event(conn, current["id"], "login")
        if error:
            raise HTTPException(401, "Invalid username or password.")
        return token

    def session(self, token):
        with closing(self.connect()) as conn:
            row = conn.execute(
                """SELECT u.id, u.username, u.role, s.expires
                FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id
                WHERE s.token = ? AND s.expires > ? AND u.active = 1""",
                (token_hash(token), time.time()),
            ).fetchone()
        return dict(row) if row else None

    def logout(self, token, actor):
        with closing(self.connect()) as conn, conn:
            conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token_hash(token),))
            self.event(conn, actor, "logout")

    def update_user(self, identifier, update: UserUpdate, actor):
        encoded = password_hash(update.password) if update.password else None
        with closing(self.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            user = conn.execute("SELECT * FROM auth_users WHERE id = ?", (identifier,)).fetchone()
            if not user:
                raise HTTPException(404, "User not found.")
            admins = conn.execute(
                "SELECT COUNT(*) FROM auth_users WHERE active = 1 AND role = 'admin'"
            ).fetchone()[0]
            if (
                user["role"] == "admin"
                and user["active"]
                and admins == 1
                and (update.role != "admin" or not update.active)
            ):
                raise HTTPException(409, "Keep at least one active administrator.")
            conn.execute(
                "UPDATE auth_users SET role = ?, active = ?, password = ? WHERE id = ?",
                (update.role, update.active, encoded or user["password"], identifier),
            )
            conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (identifier,))
            self.event(conn, actor, "user_updated_sessions_revoked", identifier)
        return {
            "id": identifier,
            "username": user["username"],
            "role": update.role,
            "active": update.active,
        }

    def change_password(self, identifier, change: PasswordChange):
        with closing(self.connect()) as conn:
            user = conn.execute(
                "SELECT password FROM auth_users WHERE id = ?", (identifier,)
            ).fetchone()
        if not user or not password_matches(change.current_password, user["password"]):
            raise HTTPException(400, "Current password is incorrect.")
        encoded = password_hash(change.password)
        with closing(self.connect()) as conn, conn:
            cursor = conn.execute(
                "UPDATE auth_users SET password = ? WHERE id = ? AND password = ?",
                (encoded, identifier, user["password"]),
            )
            if cursor.rowcount != 1:
                raise HTTPException(409, "Account changed. Sign in again.")
            conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (identifier,))
            self.event(conn, identifier, "password_changed")


def install_auth(app, path: Path):
    auth = AuthStore(path)
    app.state.auth = auth

    @app.middleware("http")
    async def permissions(request: Request, call_next):
        route = request.url.path
        public = route in {"/", "/health", "/api/v1/auth/login"} or route.startswith("/assets/")
        try:
            if request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
                raise HTTPException(403, "Use the local HealthOps address.")
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                if (
                    request.headers.get("x-healthops-request") != "1"
                    or (origin and origin != str(request.base_url).rstrip("/"))
                    or request.headers.get("sec-fetch-site") == "cross-site"
                ):
                    raise HTTPException(403, "A same-origin HealthOps request is required.")
            user = auth.session(request.cookies.get(COOKIE, ""))
            request.state.user = user
            if not public:
                if not user:
                    raise HTTPException(401, "Sign in to HealthOps.")
                if route.startswith("/api/v1/admin/") or route == "/api/v1/assistant/settings":
                    if user["role"] != "admin":
                        raise HTTPException(403, "Administrator permission required.")
                elif (
                    request.method not in {"GET", "HEAD", "OPTIONS"}
                    and not (route.startswith("/api/v1/auth/") or route.endswith("/assistant"))
                    and user["role"] not in {"reviewer", "admin"}
                ):
                    raise HTTPException(403, "Reviewer permission required.")
            response = await call_next(request)
        except HTTPException as exc:
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if route.startswith("/api/") or route in {"/docs", "/openapi.json", "/redoc"}:
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.post("/api/v1/auth/login")
    def login(body: Credentials, request: Request):
        token = auth.login(body, request.client.host if request.client else "unknown")
        response = JSONResponse(auth.session(token))
        response.set_cookie(
            COOKIE,
            token,
            max_age=SESSION_SECONDS,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            path="/",
        )
        return response

    @app.get("/api/v1/auth/me")
    def me(request: Request):
        return request.state.user

    @app.post("/api/v1/auth/logout")
    def logout(request: Request):
        auth.logout(request.cookies.get(COOKIE, ""), request.state.user["id"])
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE, path="/")
        return response

    @app.post("/api/v1/auth/password")
    def password(body: PasswordChange, request: Request):
        auth.change_password(request.state.user["id"], body)
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE, path="/")
        return response

    @app.get("/api/v1/admin/users")
    def users():
        return auth.users()

    @app.post("/api/v1/admin/users", status_code=201)
    def create_user(body: NewUser, request: Request):
        return auth.create_user(body, request.state.user["id"])

    @app.post("/api/v1/admin/users/{identifier}")
    def update_user(identifier: str, body: UserUpdate, request: Request):
        return auth.update_user(identifier, body, request.state.user["id"])

    @app.get("/api/v1/admin/events")
    def events():
        with closing(auth.connect()) as conn:
            return [
                dict(r)
                for r in conn.execute("SELECT * FROM auth_events ORDER BY id DESC LIMIT 100")
            ]


def main():
    parser = argparse.ArgumentParser(description="Create the first local administrator (once).")
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass.getpass("New password (15–128 characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")
    try:
        user = NewUser(username=args.username, password=password, role="admin")
        auth = AuthStore(Path(os.environ.get("HEALTHOPS_DB_PATH", ".local/healthops.sqlite3")))
        print(json.dumps(auth.create_user(user, bootstrap=True)))
    except (ValueError, HTTPException):
        raise SystemExit(
            "Could not create administrator. Check username/password requirements "
            "and that no account exists."
        ) from None


if __name__ == "__main__":
    main()
