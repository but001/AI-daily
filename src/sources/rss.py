"""通用 RSS 2.0 / Atom 适配器。

供多个标准 RSS 源复用：OpenAI Blog / TechCrunch AI / Hugging Face Blog / Hacker News 等。
字段映射统一按 RSS 2.0 标准字段，feedparser 会自动处理 Atom 与 RSS 的差异。

config 字段：{ id, name, url, homepage, lang, limit? }
"""
from __future__ import annotations

from typing import List

import feedparser

from ..models import NewsItem, make_id, now_iso_utc
from ._common import clean_hn_meta, http_get, parse_struct_time, strip_html


def fetch(config: dict) -> List[NewsItem]:
    url = config["url"]
    raw = http_get(url)

    feed = feedparser.parse(raw)
    if feed.bozo and feed.get("bozo_exception") and not feed.entries:
        raise RuntimeError(f"RSS 解析失败: {feed.bozo_exception}") from feed.bozo_exception

    fetched_at = now_iso_utc()
    source_name = config["name"]
    source_home = config.get("homepage", "")
    lang = config.get("lang", "en")
    limit = int(config.get("limit", 50))

    items: List[NewsItem] = []
    for entry in feed.entries[:limit]:
        link = (entry.get("link") or entry.get("guid", "")).strip()
        title = entry.get("title", "").strip()
        if not link or not title:
            continue
        # RSS 2.0: description；Atom: summary 或 content
        summary = strip_html(
            entry.get("description") or entry.get("summary") or ""
        )
        # 剥离 hnrss 元数据标签（Article URL / Comments URL / Points / Comments）
        summary, points, comments = clean_hn_meta(summary)
        published_at = parse_struct_time(entry.get("published_parsed"))

        items.append(
            NewsItem(
                id=make_id(link),
                title=title,
                original_link=link,
                source=source_name,
                source_url=source_home,
                summary=summary,
                published_at=published_at,
                fetched_at=fetched_at,
                ai_generated=False,
                lang=lang,
                points=points,
                comments=comments,
            )
        )
    return items
