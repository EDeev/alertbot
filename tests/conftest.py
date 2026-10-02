import os
import sys
import tempfile
from pathlib import Path

os.environ.update({
    "BOT_TOKEN": "123456:TEST-token-for-unit-tests-only",
    "ALLOWED_IDS": "1,2",
    "AM_ALERTS_URL": "https://example.test/ambot/api/v2/alerts",
    "PROM_QUERY_URL": "https://example.test/prombot/api/v1/query",
    "AM_TOKEN": "am-token",
    "PROM_TOKEN": "prom-token",
    "SERVERS_ORDER": "spb,ams,dorm",
    "ALERTBOT_DB": str(Path(tempfile.mkdtemp()) / "test.db"),
    "ALERT_WATCHDOG_FAILURES": "3",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

import handlers  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    with handlers.db._conn() as conn:
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM alert_seen")
    handlers.db.add_user(1, "owner")
    handlers.db.add_user(2, "friend")
    handlers.db.set_alerts(2, False)


@pytest.fixture
def sent(monkeypatch):
    """Messages the bot would send: (user_id, text)."""
    out = []

    async def fake_send(uid, text):
        out.append((uid, text))

    monkeypatch.setattr(handlers.bot, "send_message", fake_send)
    return out


@pytest.fixture
def prom(monkeypatch):
    """Fake Prometheus: maps a substring of the query to a result vector."""
    answers = {}

    async def fake_promq(session, query):
        for key, value in answers.items():
            if key in query:
                return value
        return []

    monkeypatch.setattr(handlers, "_promq", fake_promq)
    return answers


def vec(**by_server):
    return [{"metric": {"server": k}, "value": [0, str(v)]} for k, v in by_server.items()]
