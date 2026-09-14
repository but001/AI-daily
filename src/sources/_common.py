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


def parse_struct_time(struct) -> Optional[str]:
    """feedparser 的 published_parsed (time.struct_time) → ISO8601 UTC。"""
    if not struct:
        return None
    dt = datetime(*struct[:6], tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")
