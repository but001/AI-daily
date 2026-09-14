"""Hugging Face Daily Papers 源适配器。

源：https://huggingface.co/api/daily_papers
类型：公开 API（无密钥）
语言：英文（论文）

API 形态（不传 date 即返回当日 trending）：
  GET /api/daily_papers?limit=N
  返回数组，每条形如：
    {
      "paper": {
        "id": "2609.11115",          # arXiv ID
        "title": "...",
        "summary": "abstract...",   # 原生摘要
        "authors": [{"name":...}]
      },
      "publishedAt": "2026-09-14T..",# 在 HF 提交时间
      "upvotes": 193,
      "numComments": 2
    }

字段映射到 NewsItem：
  paper.title        → title
  paper.summary      → summary（原生 abstract，非AI生成 → ai_generated=False）
  paper.id           → 用于构造 original_link（https://huggingface.co/papers/<id>）
  paper.published    → published_at（arXiv 发布日期；缺失则 None）
  upvotes            → 暂存，用于热点判定（不写入 NewsItem 字段，由 build 阶段重排）
"""
from __future__ import annotations

import json
from typing import List, Optional

from ..models import NewsItem, make_id, now_iso_utc
from ._common import DEFAULT_TIMEOUT, DEFAULT_UA, http_get


def _iso(s: Optional[str]) -> Optional[str]:
    """容错地把字符串当 ISO8601 透传；空值返回 None。

    不强行解析+重排，避免时区信息丢失。源端时间已是 ISO8601 字符串时直接保留。
    """
    if not s or not isinstance(s, str):
        return None
    return s


def fetch(config: dict) -> List[NewsItem]:
    """从 Hugging Face Daily Papers API 获取当日 trending 论文。

    config 字段：{ id, name, url, homepage, lang, limit? }
    """
    base = config["url"].rstrip("/")
    limit = int(config.get("limit", 50))
    # 不传 date：API 默认返回当日 trending；保证每次跑都拿最新一份
    url = f"{base}?limit={limit}"

    raw = http_get(url)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise RuntimeError(f"HF papers API 返回非数组: {type(data).__name__}")

    fetched_at = now_iso_utc()
    source_name = config["name"]
    source_home = config.get("homepage", "https://huggingface.co/papers")
    lang = config.get("lang", "en")

    items: List[NewsItem] = []
    for entry in data:
        paper = entry.get("paper") or {}  # 兼容某些版本直接平铺
        if not paper:
            # 平铺形式：直接从 entry 取
            paper = entry

        paper_id = (paper.get("id") or entry.get("id") or "").strip()
        title = (paper.get("title") or entry.get("title", "")).strip()
        if not paper_id or not title:
            continue

        # 摘要：优先 paper.summary（原生 abstract），其次 aiSummary（AI生成则标注）
        summary = (paper.get("summary") or entry.get("summary") or "").strip()
        ai_generated = False
        if not summary:
            # 仅在无原生 abstract 时退用 AI 摘要，并标注
            ai_summary = entry.get("aiSummary") or paper.get("aiSummary")
            if ai_summary:
                summary = ai_summary.strip()
                ai_generated = True

        original_link = f"https://huggingface.co/papers/{paper_id}"
        # 发布时间：优先 paper.published（arXiv 发布日），其次 paper.publishedAt
        published_at = _iso(paper.get("published") or entry.get("publishedAt"))

        items.append(
            NewsItem(
                id=make_id(original_link),
                title=title,
                original_link=original_link,
                source=source_name,
                source_url=source_home,
                summary=summary,
                published_at=published_at,
                fetched_at=fetched_at,
                ai_generated=ai_generated,
                lang=lang,
            )
        )
    return items
