"""Exercise the actual authentication boundary, without automatic test sign-in."""

import time
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from healthops.api import create_app
from healthops.auth import COOKIE, NewUser

PASSWORD = "auth-test-only-password-123"
HEADERS = {"X-HealthOps-Request": "1"}


@pytest.fixture
def app(tmp_path):
    app = create_app(tmp_path / "auth.db")
    for role in ("admin", "reviewer", "viewer"):
        app.state.auth.create_user(NewUser(username=role, password=PASSWORD, role=role))
    return app


def login(client, role="admin", password=PASSWORD):
    return client.post(
        "/api/v1/auth/login", headers=HEADERS, json={"username": role, "password": password}
    )


def test_anonymous_cannot_read_or_mutate_and_login_never_echoes_password(app):
    with TestClient(app) as c:
        for path in (
            "/api/v1/patients",
            "/api/v1/screenings",
            "/api/v1/trials",
            "/api/v1/assistant/status",
            "/api/v1/admin/users",
            "/docs",
            "/openapi.json",
        ):
            assert c.get(path).status_code == 401
        assert c.post("/api/v1/screenings", json={}, headers=HEADERS).status_code == 401
        assert c.get("/health").status_code == 200
        r = login(c)
        assert r.status_code == 200 and PASSWORD not in r.text
        assert "httponly" in r.headers["set-cookie"].lower()
        assert "samesite=strict" in r.headers["set-cookie"].lower()
        assert c.get("/api/v1/patients").headers["cache-control"] == "no-store"
        with closing(app.state.auth.connect()) as conn:
            assert (
                conn.execute("SELECT token FROM auth_sessions").fetchone()[0] != c.cookies[COOKIE]
            )
            assert (
                PASSWORD
                not in conn.execute("SELECT password FROM auth_users LIMIT 1").fetchone()[0]
            )


@pytest.mark.parametrize("role", ["viewer", "reviewer", "admin"])
def test_role_matrix_and_forged_identity(app, role):
    with TestClient(app) as c:
        user = login(c, role).json()
        assert c.get("/api/v1/patients").status_code == 200
        assert c.get("/api/v1/trials").status_code == 200
        result = c.post("/api/v1/screenings", headers=HEADERS, json={})
        assert result.status_code == (403 if role == "viewer" else 201)
        for path, payload in (
            ("/api/v1/assistant/settings", {"provider": "offline", "model": ""}),
            (
                "/api/v1/admin/users",
                {"username": "new-user", "password": PASSWORD, "role": "admin"},
            ),
        ):
            assert c.post(path, json=payload, headers=HEADERS).status_code == (
                (201 if path.endswith("users") else 200) if role == "admin" else 403
            )
        for path in ("/api/v1/admin/users", "/api/v1/admin/events"):
            assert c.get(path).status_code == (200 if role == "admin" else 403)
        # These must deny at the boundary, even with invented resource IDs.
        if role == "viewer":
            for path in (
                "/api/v1/screenings/fake/reviews",
                "/api/v1/rule-sets/fake/reviews",
                "/api/v1/trials/fake/rule-sets",
                "/api/v1/trials/fake/rule-sets/draft",
            ):
                assert c.post(path, json={}, headers=HEADERS).status_code == 403
        else:
            review = c.post(
                f"/api/v1/screenings/{result.json()['id']}/reviews",
                headers=HEADERS,
                json={
                    "reviewer": "Impersonated administrator",
                    "decision": "request_information",
                    "reason": "Need further manual review of missing evidence.",
                },
            ).json()["reviews"][0]
            assert review["reviewer"] == role
            assert review["actor_id"] == user["id"] and review["actor_role"] == role
            assert review["identity_verification"] == "authenticated_local_account"


def test_csrf_guards_login_and_every_mutation(app):
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/v1/auth/login", json={"username": "admin", "password": PASSWORD}
            ).status_code
            == 403
        )
        login(c)
        for headers in (
            {},
            {**HEADERS, "Origin": "https://other.example"},
            {**HEADERS, "Sec-Fetch-Site": "cross-site"},
            {**HEADERS, "Host": "rebinding.example"},
        ):
            assert c.post("/api/v1/screenings", headers=headers, json={}).status_code == 403


def test_logout_expiry_and_password_change_revoke_sessions(app):
    with TestClient(app) as c, TestClient(app) as other:
        login(c)
        login(other)
        old_cookie = c.cookies[COOKIE]
        assert c.post("/api/v1/auth/logout", json={}, headers=HEADERS).status_code == 200
        assert app.state.auth.session(old_cookie) is None
        login(c)
        r = c.post(
            "/api/v1/auth/password",
            headers=HEADERS,
            json={"current_password": PASSWORD, "password": PASSWORD + "-changed"},
        )
        assert r.status_code == 200
        assert other.get("/api/v1/auth/me").status_code == 401
        assert login(c, password=PASSWORD).status_code == 401
        assert login(c, password=PASSWORD + "-changed").status_code == 200
        with closing(app.state.auth.connect()) as conn, conn:
            conn.execute("UPDATE auth_sessions SET expires = ?", (time.time() - 1,))
        assert c.get("/api/v1/patients").status_code == 401


def test_disable_and_role_change_revoke_sessions_and_last_admin_is_protected(app):
    with TestClient(app) as admin, TestClient(app) as reviewer:
        boss = login(admin).json()
        actor = login(reviewer, "reviewer").json()
        url = f"/api/v1/admin/users/{actor['id']}"
        assert (
            admin.post(url, headers=HEADERS, json={"role": "viewer", "active": True}).status_code
            == 200
        )
        assert reviewer.get("/api/v1/patients").status_code == 401
        assert login(reviewer, "reviewer").json()["role"] == "viewer"
        assert reviewer.post("/api/v1/screenings", headers=HEADERS, json={}).status_code == 403
        assert (
            admin.post(url, headers=HEADERS, json={"role": "viewer", "active": False}).status_code
            == 200
        )
        assert login(reviewer, "reviewer").status_code == 401
        assert (
            admin.post(
                f"/api/v1/admin/users/{boss['id']}",
                headers=HEADERS,
                json={"role": "viewer", "active": False},
            ).status_code
            == 409
        )
        assert admin.get("/api/v1/auth/me").status_code == 200


def test_throttling_and_generic_invalid_login(app):
    with TestClient(app) as c:
        for _ in range(5):
            assert (
                login(c, "missing", "incorrect").json()["detail"] == "Invalid username or password."
            )
        assert login(c, "missing", "incorrect").status_code == 429
        assert login(c).status_code == 200


def test_bootstrap_not_available_after_first_account_and_secure_cookie_on_https(app):
    with pytest.raises(Exception) as caught:
        app.state.auth.create_user(
            NewUser(username="takeover", password=PASSWORD, role="admin"), bootstrap=True
        )
    assert caught.value.status_code == 409
    with TestClient(app, base_url="https://localhost") as c:
        assert "Secure" in login(c).headers["set-cookie"]


def test_rule_review_uses_session_identity(app):
    with TestClient(app) as c:
        user = login(c, "reviewer").json()
        trial = c.get("/api/v1/trials?source=registry").json()[0]
        rules = c.post(
            f"/api/v1/trials/{trial['id']}/rule-sets/draft", json={}, headers=HEADERS
        ).json()
        r = c.post(
            f"/api/v1/rule-sets/{rules['id']}/reviews",
            headers=HEADERS,
            json={
                "reviewer": "Forged identity",
                "decision": "reject",
                "reason": "Synthetic automated test of reviewer attribution.",
                "expected_rules_hash": rules["rules_hash"],
            },
        )
        assert r.status_code == 201
        assert r.json()["review"]["actor_id"] == user["id"]
        assert r.json()["review"]["reviewer"] == "reviewer"
