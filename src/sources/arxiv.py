"""ArXiv cs.AI 源适配器。

源：http://export.arxiv.org/api/query
类型：公开 API（Atom XML，feedparser 解析）
语言：英文（学术论文）

稳定公开的国际 API，CI 容器可访问。用于替代失效的机器之心 RSS。

字段映射：
  entry.title    → NewsItem.title
  entry.link     → NewsItem.original_link (http://arxiv.org/abs/<id>)
  entry.summary  → NewsItem.summary（原生 abstract）
  entry.published → NewsItem.published_at（ISO8601）
"""
from __future__ import annotations

from typing import List

import feedparser

from ..models import NewsItem, make_id, now_iso_utc
from ._common import DEFAULT_TIMEOUT, DEFAULT_UA, http_get, parse_struct_time


def fetch(config: dict) -> List[NewsItem]:
    """从 ArXiv cs.AI 获取最新论文。

    config 字段：{ id, name, url, homepage, lang, limit? }
    """
    base = config["url"].rstrip("/")
    limit = int(config.get("limit", 50))
    url = (
        f"{base}?search_query=cat:cs.AI&start=0&max_results={limit}"
        "&sortBy=submittedDate&sortOrder=descending"
    )

    raw = http_get(url)
    feed = feedparser.parse(raw)

    # ArXiv API 返回的是合法 Atom XML，正常情况下不会 bozo
    if feed.bozo and feed.get("bozo_exception") and not feed.entries:
        raise RuntimeError(f"ArXiv 解析失败: {feed.bozo_exception}") from feed.bozo_exception

    fetched_at = now_iso_utc()
    source_name = config["name"]
    source_home = config.get("homepage", "https://arxiv.org/list/cs.AI/recent")
    lang = config.get("lang", "en")

    items: List[NewsItem] = []
    for entry in feed.entries:
        link = (entry.get("link") or entry.get("id", "")).strip()
        title = entry.get("title", "").strip()
        if not link or not title:
            continue
        summary = entry.get("summary", "").strip()
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
            )
        )
    return items
