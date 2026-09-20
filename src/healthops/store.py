"""Small local review ledger. Authenticated decisions; not tamper-proof audit storage."""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from healthops.screening import _hash


class ReviewStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS screenings (
                    id TEXT PRIMARY KEY, snapshot TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    screening_id TEXT NOT NULL REFERENCES screenings(id),
                    revision INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    UNIQUE(screening_id, revision)
                );
                CREATE TABLE IF NOT EXISTS rule_sets (
                    id TEXT PRIMARY KEY, trial_id TEXT NOT NULL, snapshot TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rule_reviews (
                    rule_set_id TEXT PRIMARY KEY REFERENCES rule_sets(id), event TEXT NOT NULL
                );
            """)

    @staticmethod
    def identity(actor: dict | None, request: dict) -> dict:
        if actor is None:
            return {"identity_verification": "self_reported_demo_only"}
        return {
            "reviewer": actor["username"],
            "actor_id": actor["id"],
            "actor_role": actor["role"],
            "identity_verification": "authenticated_local_account",
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def save_rule_set(self, document: dict) -> dict:
        identifier = _hash(document)
        snapshot = {
            "id": identifier,
            "rules_hash": identifier,
            "document": document,
            "created_at": datetime.now(UTC).isoformat(),
        }
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR IGNORE INTO rule_sets VALUES (?, ?, ?)",
                (identifier, document["trial_id"], json.dumps(snapshot)),
            )
        return self.get_rule_set(identifier)

    def get_rule_set(self, identifier: str) -> dict:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT snapshot FROM rule_sets WHERE id = ?", (identifier,)
            ).fetchone()
            review = conn.execute(
                "SELECT event FROM rule_reviews WHERE rule_set_id = ?", (identifier,)
            ).fetchone()
        if row is None:
            raise KeyError("Rule set not found.")
        result = json.loads(row[0])
        result["review"] = json.loads(review[0]) if review else None
        result["status"] = {"approve": "approved", "reject": "rejected"}.get(
            result["review"]["decision"] if review else None, "pending_review"
        )
        return result

    def list_rule_sets(self, trial_id: str) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id FROM rule_sets WHERE trial_id = ? ORDER BY rowid", (trial_id,)
            ).fetchall()
        return [self.get_rule_set(row[0]) for row in rows]

    def review_rule_set(self, identifier: str, request: dict, *, actor: dict | None = None) -> dict:
        snapshot = self.get_rule_set(identifier)
        if request["expected_rules_hash"] != snapshot["rules_hash"]:
            raise ValueError("Rules hash mismatch. Reload the interpretation before review.")
        event = {
            **request,
            "id": str(uuid4()),
            "recorded_at": datetime.now(UTC).isoformat(),
            **self.identity(actor, request),
            "snapshot_id": snapshot["document"]["snapshot_id"],
        }
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT INTO rule_reviews VALUES (?, ?)", (identifier, json.dumps(event))
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "This interpretation was already reviewed. Submit a new version to change it."
            ) from exc
        return self.get_rule_set(identifier)

    def save_screening(self, result: dict, bundle: dict, trial: dict) -> dict:
        result = {
            **result,
            "id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
            "source_snapshot": {"patient_bundle": bundle, "trial": trial},
        }
        with closing(self._connect()) as conn, conn:
            conn.execute("INSERT INTO screenings VALUES (?, ?)", (result["id"], json.dumps(result)))
        return self.get_screening(result["id"])

    def list_screenings(self, limit: int = 50, offset: int = 0) -> dict:
        """Return compact history without shipping every stored clinical snapshot."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT s.id, json_extract(s.snapshot, '$.patient_id'),
                    json_extract(s.snapshot, '$.trial_id'),
                    json_extract(s.snapshot, '$.created_at'),
                    json_extract(s.snapshot, '$.as_of'),
                    json_extract(s.snapshot, '$.outcome'),
                    COALESCE(json_extract(s.snapshot, '$.data_source'), 'fixtures'),
                    COALESCE((SELECT json_extract(r.event, '$.decision') FROM reviews r
                        WHERE r.screening_id = s.id ORDER BY r.revision DESC LIMIT 1),
                        'pending_review')
                FROM screenings s ORDER BY s.rowid DESC LIMIT ? OFFSET ?
            """,
                (limit, offset),
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM screenings").fetchone()[0]
            pending = conn.execute("""SELECT COUNT(*) FROM screenings s WHERE NOT EXISTS
                (SELECT 1 FROM reviews r WHERE r.screening_id = s.id)""").fetchone()[0]
        fields = (
            "id",
            "patient_id",
            "trial_id",
            "created_at",
            "as_of",
            "outcome",
            "data_source",
            "review_status",
        )
        return {
            "items": [dict(zip(fields, row, strict=True)) for row in rows],
            "total": total,
            "pending_count": pending,
            "limit": limit,
            "offset": offset,
        }

    def get_screening(self, screening_id: str) -> dict:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT snapshot FROM screenings WHERE id = ?", (screening_id,)
            ).fetchone()
            if row is None:
                raise KeyError(screening_id)
            events = conn.execute(
                "SELECT event FROM reviews WHERE screening_id = ? ORDER BY revision",
                (screening_id,),
            ).fetchall()
        result = json.loads(row[0])
        result["reviews"] = [json.loads(event[0]) for event in events]
        result["revision"] = len(events)
        if result["reviews"]:
            result["review_status"] = result["reviews"][-1]["decision"]
        return result

    def add_review(self, screening_id: str, request: dict, *, actor: dict | None = None) -> dict:
        snapshot = self.get_screening(screening_id)
        revision = request.pop("expected_revision")
        if revision != snapshot["revision"]:
            raise ValueError("A newer review exists. Reload the screening before submitting.")
        event = {
            **request,
            "id": str(uuid4()),
            "screening_id": screening_id,
            "revision": revision + 1,
            "recorded_at": datetime.now(UTC).isoformat(),
            **self.identity(actor, request),
            "rules_version": snapshot["rules_version"],
            "rules_hash": snapshot["rules_hash"],
            "evidence_hash": snapshot["evidence_hash"],
        }
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT INTO reviews VALUES (?, ?, ?, ?)",
                    (event["id"], screening_id, revision + 1, json.dumps(event)),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("A newer review exists. Reload before submitting.") from exc
        return self.get_screening(screening_id)
