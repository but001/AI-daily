"""采集调度测试：单源失败不影响其他源 + fetch_log 写入。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import fetch as fetch_mod  # noqa: E402
from src.models import NewsItem  # noqa: E402


def _fake_item(link: str, source: str = "test") -> NewsItem:
    return NewsItem(
        id="x" + link[-4:],
        title="T " + link,
        original_link=link,
        source=source,
        source_url="",
        fetched_at="2026-09-14T00:00:00+00:00",
    )


def test_single_source_failure_does_not_block_others(tmp_path, monkeypatch):
    """单源失败：其他源应正常返回，旧数据不被清空。"""
    # 重定向 fetch_log 到临时目录
    log_path = tmp_path / "fetch_log.json"
    monkeypatch.setattr(fetch_mod, "FETCH_LOG_PATH", log_path)

    # mock 两个源：A 抛错，B 正常返回
    def fake_route(sid):
        if sid == "ok_src":
            m = mock.MagicMock()
            m.fetch.return_value = [_fake_item("https://ok/0001", "ok_src")]
            return m
        elif sid == "bad_src":
            m = mock.MagicMock()
            m.fetch.side_effect = RuntimeError("simulated network error")
            return m
        raise AssertionError(f"unexpected id: {sid}")

    monkeypatch.setattr(fetch_mod, "_route_adapter", fake_route)
    monkeypatch.setattr(
        fetch_mod,
        "load_sources",
        lambda: [
            {"id": "ok_src", "name": "OK", "url": "x", "homepage": "", "lang": "zh"},
            {"id": "bad_src", "name": "BAD", "url": "y", "homepage": "", "lang": "zh"},
        ],
    )

    r = fetch_mod.fetch_all()
    assert "ok_src" in r.status and r.status["ok_src"] == "ok"
    assert r.status["bad_src"].startswith("fail")
    # 失败的源不应阻断其他源：来自 ok_src 的条目应在
    assert len(r.items) == 1
    assert r.items[0].source == "ok_src"


def test_fetch_log_records_run_status(tmp_path, monkeypatch):
    """fetch_log 应记录每次运行的状态。"""
    log_path = tmp_path / "fetch_log.json"
    monkeypatch.setattr(fetch_mod, "FETCH_LOG_PATH", log_path)
    monkeypatch.setattr(
        fetch_mod, "load_sources",
        lambda: [{"id": "ok_src", "name": "OK", "url": "x", "homepage": "", "lang": "zh"}],
    )
    monkeypatch.setattr(fetch_mod, "_route_adapter", lambda sid: mock.MagicMock(
        fetch=mock.MagicMock(return_value=[])))

    fetch_mod.fetch_all()
    assert log_path.exists()
    log = json.loads(log_path.read_text(encoding="utf-8"))
    assert len(log) == 1
    run_key = list(log.keys())[0]
    assert log[run_key]["ok_src"] == "ok"


def test_latest_run_summary_returns_most_recent(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_mod, "FETCH_LOG_PATH", tmp_path / "fetch_log.json")
    monkeypatch.setattr(fetch_mod, "load_sources", lambda: [])
    monkeypatch.setattr(fetch_mod, "_route_adapter", lambda sid: None)
    fetch_mod.fetch_all()

    s = fetch_mod.latest_run_summary()
    assert "fetched_at" in s
    assert s["status"] == {}
