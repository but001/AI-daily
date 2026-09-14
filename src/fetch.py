"""采集调度：加载 sources 配置 → 调用各源适配器 → 汇总 + 容错。

容错原则：
- 单源失败不阻断其他源：try/except 包住每个源
- 失败状态记入 fetch_log，便于界面展示"最近更新状态"
- 不返回部分失败的整体错误；让上层继续用已成功的条目
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import yaml

from .models import NewsItem, now_iso_utc

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
FETCH_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "fetch_log.json"
# 保留最近 N 次运行记录，避免 fetch_log 无限增长
MAX_RUN_LOG = 30


@dataclass
class FetchResult:
    items: List[NewsItem] = field(default_factory=list)
    # {"source_id": "ok" | "fail: <msg>"} —— 失败含简短原因
    status: dict = field(default_factory=dict)
    fetched_at: str = ""


def load_sources() -> list[dict]:
    """读取 config/sources.yaml，仅返回 enabled 的源。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    sources = cfg.get("sources", []) if cfg else []
    return [s for s in sources if s.get("enabled", True)]


def _route_adapter(source: dict):
    """路由到对应适配器模块。

    优先看 source['adapter']，否则用 source['id']。
    约定：适配器模块名 == 该字段值。如 rss → src.sources.rss；arxiv → src.sources.arxiv
    """
    mod_name = source.get("adapter") or source["id"]
    return importlib.import_module(f".sources.{mod_name}", package="src")


def fetch_all() -> FetchResult:
    """采集所有启用的源，单源失败不影响其他。"""
    sources = load_sources()
    result = FetchResult(fetched_at=now_iso_utc())

    for src in sources:
        sid = src["id"]
        try:
            adapter = _route_adapter(src)
            items = adapter.fetch(src)
            result.items.extend(items)
            result.status[sid] = "ok"
        except Exception as e:  # 单源失败：记原因，继续
            result.status[sid] = f"fail: {type(e).__name__}: {e}"

    _append_fetch_log(result)
    return result


def _append_fetch_log(result: FetchResult) -> None:
    """把本次运行状态追加到 data/fetch_log.json，保留最近 MAX_RUN_LOG 次。"""
    FETCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log: dict = {}
    if FETCH_LOG_PATH.exists():
        try:
            log = json.loads(FETCH_LOG_PATH.read_text(encoding="utf-8"))
            if not isinstance(log, dict):
                log = {}
        except Exception:
            log = {}

    log[result.fetched_at] = result.status
    # 保留最近 MAX_RUN_LOG 次运行（按时间倒序后切片）
    keys = sorted(log.keys(), reverse=True)[:MAX_RUN_LOG]
    log = {k: log[k] for k in keys}

    FETCH_LOG_PATH.write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def latest_run_summary() -> dict:
    """返回最近一次运行的状态，供界面"最近更新状态"展示。"""
    if not FETCH_LOG_PATH.exists():
        return {}
    try:
        log = json.loads(FETCH_LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not log:
        return {}
    latest_key = max(log.keys())
    return {"fetched_at": latest_key, "status": log[latest_key]}
