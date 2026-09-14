"""机器之心 RSS 源适配器。

源：https://www.jiqizhixin.com/rss
类型：RSS（媒体）
语言：中文

字段映射：
  entry.title            → NewsItem.title
  entry.link             → NewsItem.original_link
  entry.summary          → NewsItem.summary（HTML 清洗为纯文本）
  entry.published_parsed → NewsItem.published_at（UTC ISO8601，缺失则 None）

缺失字段处理：
- published_parsed 缺失：published_at 留 None，由界面标注"发布时间未知"
- summary 缺失：留空字符串
"""
from __future__ import annotations

from typing import List

import feedparser

from ..models import NewsItem, make_id, now_iso_utc
from ._common import http_get, parse_struct_time, strip_html


def fetch(config: dict) -> List[NewsItem]:
    """从机器之心 RSS 获取资讯。

    config 字段：{ id, name, url, homepage, lang }
    失败时抛异常，由上层调度捕获并标记来源失败。
    """
    raw = http_get(config["url"])
    feed = feedparser.parse(raw)

    if feed.bozo and feed.get("bozo_exception"):
        # 解析告警但不一定致命：若有 entries 则继续，否则抛错
        if not feed.entries:
            raise RuntimeError(
                f"RSS 解析失败: {feed.bozo_exception}"
            ) from feed.bozo_exception

    fetched_at = now_iso_utc()
    source_name = config["name"]
    source_home = config.get("homepage", "")
    lang = config.get("lang", "zh")

    items: List[NewsItem] = []
    for entry in feed.entries:
        link = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not link or not title:
            # 必要字段缺失则跳过本条（题目要求处理缺失字段）
            continue
        summary = strip_html(entry.get("summary", "") or entry.get("description", ""))
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
                ai_generated=False,  # 来自源原生摘要，非AI生成
                lang=lang,
            )
        )
    return items
