import asyncio

import handlers


def alert(fp, name="NodeDown", state="active", server="spb", summary="Узел не отвечает"):
    return {"fingerprint": fp, "status": {"state": state},
            "labels": {"alertname": name, "severity": "critical", "server": server},
            "annotations": {"summary": summary}}


def run(coro):
    return asyncio.run(coro)


def test_new_alert_is_sent_once_to_subscribers(sent):
    run(handlers.process_alerts([alert("a1")]))
    run(handlers.process_alerts([alert("a1")]))
    assert [uid for uid, _ in sent] == [1]
    assert "Проблема · NodeDown" in sent[0][1]


def test_resolved_alert_is_announced(sent):
    run(handlers.process_alerts([alert("a1")]))
    run(handlers.process_alerts([]))
    assert "В норме · NodeDown" in sent[-1][1]
    assert handlers.db.list_firing_fingerprints() == []


def test_suppressed_alerts_are_ignored(sent):
    run(handlers.process_alerts([alert("a1", state="suppressed"), {"status": {"state": "active"}}]))
    assert sent == []


def test_alert_text_is_html_escaped():
    text = handlers._fmt_firing(alert("a1", name="<b>x</b>", summary="a < b & c"))
    assert "&lt;b&gt;x&lt;/b&gt;" in text
    assert "a &lt; b &amp; c" in text


def test_watchdog_reports_once_and_recovers(sent):
    wd = handlers.Watchdog(threshold=3)
    for _ in range(5):
        run(wd.failed("timeout"))
    assert len(sent) == 1 and "Мониторинг недоступен" in sent[0][1]
    run(wd.ok())
    assert "Мониторинг снова доступен" in sent[-1][1]
    run(wd.ok())
    assert len(sent) == 2


def test_watchdog_ignores_short_glitches(sent):
    wd = handlers.Watchdog(threshold=3)
    run(wd.failed("timeout"))
    run(wd.failed("timeout"))
    run(wd.ok())
    assert sent == []


def test_token_is_sent_in_header_not_url():
    assert handlers._auth("secret") == {"Authorization": "Bearer secret"}
