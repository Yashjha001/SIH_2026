"""Small durable repository for the single-user MVP; no account/auth claims."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from .schemas import CommunityObservation, ObservationInput, UserProfile


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = str(path or os.getenv("MAUSAM_DB_PATH", str(Path(__file__).resolve().parents[1] / "mausam_plus.db")))
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, location TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS reads (user_id TEXT NOT NULL, alert_id TEXT NOT NULL, PRIMARY KEY(user_id, alert_id))")
            db.execute("INSERT OR IGNORE INTO profiles VALUES (?, ?)", ("demo-user", UserProfile().model_dump_json()))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def profile(self, user_id: str) -> UserProfile | None:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM profiles WHERE id=?", (user_id,)).fetchone()
        return UserProfile.model_validate_json(row[0]) if row else None

    def save_profile(self, profile: UserProfile) -> UserProfile:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO profiles VALUES (?, ?)", (profile.id, profile.model_dump_json()))
        return profile

    def report(self, item: ObservationInput) -> CommunityObservation:
        now = datetime.now(timezone.utc).isoformat()
        report = CommunityObservation(id=str(uuid4()), type=item.type, location=item.location.strip(),
            reported_at=now, area=item.area.strip(), details=item.details.strip())
        with self.connect() as db:
            db.execute("INSERT INTO reports VALUES (?, ?, ?, ?)",
                (report.id, report.location.casefold(), now, report.model_dump_json()))
        return report

    def reports(self, location: str) -> list[CommunityObservation]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM reports WHERE location=? AND created>=? ORDER BY created DESC LIMIT 50",
                (location.strip().casefold(), cutoff)).fetchall()
        return [CommunityObservation.model_validate_json(row[0]) for row in rows]

    def read_ids(self, user_id: str) -> set[str]:
        with self.connect() as db:
            return {row[0] for row in db.execute("SELECT alert_id FROM reads WHERE user_id=?", (user_id,))}

    def mark_read(self, user_id: str, alert_id: str):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO reads VALUES (?, ?)", (user_id, alert_id))
