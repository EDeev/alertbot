import sqlite3
from typing import List, Optional, Tuple


class DatabaseManager:
    def __init__(self, db_path: str = "notifications.db"):
        self.db_path = db_path
        self.init_database()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def init_database(self):
        with self._conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    alerts_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alert_seen (
                    fingerprint TEXT PRIMARY KEY,
                    status TEXT,
                    name TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    # ---------- users ----------
    def add_user(self, user_id: int, username: str) -> bool:
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO users (user_id, username) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username",
                    (user_id, username),
                )
                conn.commit()
            return True
        except sqlite3.Error:
            return False

    def set_alerts(self, user_id: int, value: bool) -> bool:
        try:
            with self._conn() as conn:
                conn.execute("UPDATE users SET alerts_enabled = ? WHERE user_id = ?",
                             (1 if value else 0, user_id))
                conn.commit()
            return True
        except sqlite3.Error:
            return False

    def get_user_info(self, user_id: int) -> Optional[Tuple]:
        """(user_id, username, alerts_enabled)"""
        try:
            with self._conn() as conn:
                return conn.execute(
                    "SELECT user_id, username, alerts_enabled FROM users WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
        except sqlite3.Error:
            return None

    def get_alert_users(self) -> List[int]:
        try:
            with self._conn() as conn:
                return [r[0] for r in conn.execute(
                    "SELECT user_id FROM users WHERE alerts_enabled = 1"
                ).fetchall()]
        except sqlite3.Error:
            return []

    # ---------- alert dedup ----------
    def get_alert_status(self, fingerprint: str) -> Optional[str]:
        try:
            with self._conn() as conn:
                r = conn.execute("SELECT status FROM alert_seen WHERE fingerprint = ?",
                                 (fingerprint,)).fetchone()
                return r[0] if r else None
        except sqlite3.Error:
            return None

    def upsert_alert(self, fingerprint: str, status: str, name: str):
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO alert_seen (fingerprint, status, name, updated_at) "
                    "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(fingerprint) DO UPDATE SET status=excluded.status, "
                    "name=excluded.name, updated_at=CURRENT_TIMESTAMP",
                    (fingerprint, status, name),
                )
                conn.commit()
        except sqlite3.Error:
            pass

    def list_firing_fingerprints(self) -> List[Tuple[str, str]]:
        try:
            with self._conn() as conn:
                return conn.execute(
                    "SELECT fingerprint, name FROM alert_seen WHERE status = 'firing'"
                ).fetchall()
        except sqlite3.Error:
            return []

    def purge_old_resolved(self, days: int = 3):
        try:
            with self._conn() as conn:
                conn.execute(
                    "DELETE FROM alert_seen WHERE status = 'resolved' "
                    "AND updated_at < datetime('now', ?)", (f'-{days} days',))
                conn.commit()
        except sqlite3.Error:
            pass
