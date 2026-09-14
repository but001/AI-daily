"""智源社区 RSS 源适配器。

源：https://hub.baai.ac.cn/rss
类型：RSS 2.0（feedparser 解析）
语言：中文（国内 AI 学术社区）

智源社区是北京智源研究院运营的 AI 学术社区，内容覆盖论文解读、
模型实现、研究方法等。RSS 返回的是 HTML 编码字符实体，
feedparser 会自动解码为正常 UTF-8。

字段映射：
  entry.title        → NewsItem.title
  entry.link         → NewsItem.original_link
  entry.description  → NewsItem.summary（HTML，strip tags）
  entry.pubDate      → NewsItem.published_at（RFC822 → ISO8601）
"""
from __future__ import annotations

from typing import List

import feedparser

from ..models import NewsItem, make_id, now_iso_utc
from ._common import DEFAULT_TIMEOUT, DEFAULT_UA, http_get, parse_struct_time, strip_html


def fetch(config: dict) -> List[NewsItem]:
    """从智源社区 RSS 获取最新内容。

    config 字段：{ id, name, url, homepage, lang, limit? }
    """
    url = config["url"]
    raw = http_get(url)

    feed = feedparser.parse(raw)
    if feed.bozo and feed.get("bozo_exception") and not feed.entries:
        raise RuntimeError(f"智源 RSS 解析失败: {feed.bozo_exception}") from feed.bozo_exception

    fetched_at = now_iso_utc()
    source_name = config["name"]
    source_home = config.get("homepage", "https://hub.baai.ac.cn")
    lang = config.get("lang", "zh")
    limit = int(config.get("limit", 50))

    items: List[NewsItem] = []
    for entry in feed.entries[:limit]:
        link = (entry.get("link") or entry.get("guid", "")).strip()
        title = entry.get("title", "").strip()
        if not link or not title:
            continue
        summary = strip_html(entry.get("description", ""))
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
