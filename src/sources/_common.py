"""源适配器共享工具。"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Optional

import requests

# 统一 UA，避免被源站点基础拦截
DEFAULT_UA = (
    "Mozilla/5.0 (compatible; AI-Daily-Bot/1.0; "
    "+https://github.com/ai-daily)"
)
DEFAULT_TIMEOUT = 20  # 秒


def http_get(url: str, **kwargs) -> str:
    """统一的 HTTP GET，固定 UA 与超时。失败抛 requests.RequestException。"""
    headers = kwargs.pop("headers", {"User-Agent": DEFAULT_UA})
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    resp = requests.get(url, headers=headers, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp.text


def strip_html(text: str) -> str:
    """去除 HTML 标签并反转义实体，得到纯文本摘要。"""
    if not text:
        return ""
    # 块级标签换行，便于阅读
    text = re.sub(r"</(p|div|br|li|h\d)>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# hnrss（Hacker News RSS）的 description 会把元数据拼接进文本：
#   "Article URL: <url> Comments URL: <url> Points: N # Comments: M"
# 这些是标签而非正文，需剥离；Points/Comments 则提取为独立字段。
_HN_POINTS = re.compile(r"Points:\s*(\d+)", re.I)
_HN_COMMENTS = re.compile(r"#\s*Comments:\s*(\d+)", re.I)
_HN_ARTICLE_URL = re.compile(r"Article\s+URL:\s*\S+", re.I)
_HN_COMMENTS_URL = re.compile(r"Comments\s+URL:\s*\S+", re.I)


def clean_hn_meta(text: str) -> tuple[str, int | None, int | None]:
    """剥离 hnrss 元数据标签，返回 (纯正文, points, comments)。

    对不含这些标签的普通摘要保持原样返回，points/comments 为 None。
    """
    if not text:
        return "", None, None

    m = _HN_POINTS.search(text)
    points = int(m.group(1)) if m else None
    m = _HN_COMMENTS.search(text)
    comments = int(m.group(1)) if m else None

    cleaned = _HN_COMMENTS_URL.sub(" ", text)
    cleaned = _HN_ARTICLE_URL.sub(" ", cleaned)
    cleaned = _HN_POINTS.sub(" ", cleaned)
    cleaned = _HN_COMMENTS.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, points, comments


def parse_struct_time(struct) -> Optional[str]:
    """feedparser 的 published_parsed (time.struct_time) → ISO8601 UTC。"""
    if not struct:
        return None
    dt = datetime(*struct[:6], tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")
