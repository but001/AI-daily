"""静态站点构建：读取 news.json + fetch_log → 渲染 Jinja2 模板 → 输出到 _site/。

输出：
- _site/index.html         主列表页（含全部新闻 + 嵌入 JSON 供 JS 筛选）
- _site/data/news.json     嵌入式数据副本（供前端 fetch/筛选）
- _site/data/fetch_log.json 最近更新状态
- _site/my-reading.html    我的阅读页（纯静态壳，JS 从 localStorage 渲染）
- _site/static/             CSS/JS/图标

每日热点启发式：
- 关键词加权（release/open source/SOTA/GPT/LLM/新模型/发布/开源/突破）
- 当日发布加分；不同来源各取最多1条避免单源垄断
- 取 top 3，标记 is_hot=True
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import fetch as fetch_mod
from . import dedupe as dedupe_mod
from .models import now_iso_utc
from .sources._common import clean_hn_meta

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
STATIC_SRC = ROOT / "static"
OUT_DIR = ROOT / "_site"

DISPLAY_TZ = "Asia/Shanghai"

# 热点关键词
HOT_KEYWORDS = [
    "release", "open source", "open-source", "opensource",
    "SOTA", "state-of-the-art",
    "GPT", "LLM", "language model",
    "新模型", "发布", "开源", "突破", "升级",
]


def _today_date_str() -> str:
    """今日日期（北京时区），用于归档命名。"""
    from datetime import timedelta
    utc_now = datetime.now(tz=timezone.utc)
    # 北京时间 = UTC+8
    beijing = utc_now + timedelta(hours=8)
    return beijing.strftime("%Y-%m-%d")


def _is_today(published_at: str | None, today: str) -> bool:
    if not published_at:
        return False
    # ISO8601 字符串前 10 位即日期
    return published_at[:10] == today


def _score_hot(item: dict, today: str) -> float:
    """启发式打分；分数越高越值得看。"""
    title = (item.get("title") or "").lower()
    summary = (item.get("summary") or "").lower()
    score = 0.0
    for kw in HOT_KEYWORDS:
        if kw.lower() in title:
            score += 2.0
        if kw.lower() in summary:
            score += 0.5
    if item.get("published_at"):
        score += 0.5
        if _is_today(item["published_at"], today):
            score += 3.0  # 当日发布优先
    return score


def mark_hot(items: List[dict], top_n: int = 3) -> List[dict]:
    """标记 top_n 条热点；限制同源最多1条，避免单源垄断。"""
    today = _today_date_str()
    scored = sorted(
        enumerate(items),
        key=lambda p: (_score_hot(p[1], today), p[1].get("published_at") or ""),
        reverse=True,
    )

    picked: list[int] = []
    picked_sources: set[str] = set()
    for idx, item in scored:
        if len(picked) >= top_n:
            break
        # 同源最多1条；但若评分高明显领先可破例
        src = item.get("source") or ""
        if src in picked_sources:
            continue
        picked.append(idx)
        picked_sources.add(src)

    for i, item in enumerate(items):
        item["is_hot"] = i in picked
    return items


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["fmt_time"] = _fmt_time
    return env


def _fmt_time(iso: str | None) -> str:
    """ISO8601 → 北京时区 'YYYY-MM-DD HH:MM'；None → '发布时间未知'。"""
    if not iso:
        return "发布时间未知"
    try:
        # 兼容有时区/无时区两种写法
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        from datetime import timedelta
        beijing = dt + timedelta(hours=8)
        return beijing.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso  # 解析失败保留原值，不编造


def build_site() -> None:
    """构建静态站点到 _site/。"""
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 读取数据
    news = dedupe_mod.load_news()  # List[dict]
    # 兜底清洗：旧 data/news.json 中可能残留未剥离的 hnrss 元数据标签
    # （fetch 阶段已清洗新数据，这里只处理历史遗留，避免界面显示裸链接）
    for item in news:
        cleaned, points, comments = clean_hn_meta(item.get("summary") or "")
        item["summary"] = cleaned
        if points is not None:
            item["points"] = points
        if comments is not None:
            item["comments"] = comments
    news = mark_hot(news, top_n=3)
    fetch_log = {}
    fp = dedupe_mod.NEWS_PATH.parent / "fetch_log.json"
    if fp.exists():
        try:
            fetch_log = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            fetch_log = {}

    # 最近一次运行的状态（界面顶部展示）
    latest_run = fetch_mod.latest_run_summary()

    # 2) 复制静态资源
    if STATIC_SRC.exists():
        shutil.copytree(STATIC_SRC, OUT_DIR / "static")

    # 3) 数据副本（前端可 fetch）
    data_out = OUT_DIR / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    (data_out / "news.json").write_text(
        json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (data_out / "fetch_log.json").write_text(
        json.dumps(fetch_log, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4) 渲染主页
    env = _make_env()
    sources = [s for s in fetch_mod.load_sources()]
    source_filter = [{"id": s["id"], "name": s["name"]} for s in sources]

    # 按发布日期分组（用于前端按天展示）
    tpl_index = env.get_template("index.html.j2")
    html = tpl_index.render(
        items=news,
        source_filter=source_filter,
        latest_run=latest_run,
        today=_today_date_str(),
        recent_days=7,
        built_at=now_iso_utc(),
    )
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")

    # 5) 渲染「我的阅读」页（纯静态壳，列表由 JS 从 localStorage 渲染）
    tpl_reading = env.get_template("my-reading.html.j2")
    html = tpl_reading.render(built_at=now_iso_utc(), today=_today_date_str())
    (OUT_DIR / "my-reading.html").write_text(html, encoding="utf-8")


def build_all() -> None:
    """完整流程入口：构建站点。"""
    build_site()


if __name__ == "__main__":
    build_all()
