"""数据模型：NewsItem 与相关校验/归一化工具。

设计原则：
- 字段缺失必须可表达（published_at 缺失用 None，界面标注"发布时间未知"）
- 不在模型层编造事实；摘要/翻译是否AI生成必须显式标注 ai_generated
- 去重主键基于 URL 规范化后的 sha1，确保同链接不同 query 不被当作两条
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """URL 规范化：去 fragment、去 query、去末尾斜杠、scheme/host 小写。

    不保留 query 的理由：utm_source 等跟踪参数会让"同一篇文章"被识别为
    多条；本项目两个源（机器之心 RSS、HF Papers）链接均不含文章 ID 类 query，
    去掉 query 不影响生产去重，反而提升跨源同文章聚合。
    """
    if not url:
        return ""
    url = url.strip()
    parts = urlsplit(url)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, "", ""))


def normalize_title(title: str) -> str:
    """标题归一化：去所有空白并小写，用于次级去重判断。"""
    if not title:
        return ""
    return re.sub(r"\s+", "", title).lower()


def make_id(original_link: str) -> str:
    """根据原文链接生成稳定 ID（URL 规范化后 sha1）。"""
    return hashlib.sha1(normalize_url(original_link).encode("utf-8")).hexdigest()[:16]


def now_iso_utc() -> str:
    """采集时间口径：UTC，ISO8601 带时区。"""
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


@dataclass
class NewsItem:
    id: str = ""
    title: str = ""
    original_link: str = ""
    source: str = ""
    source_url: str = ""
    fetched_at: str = ""
    summary: str = ""
    published_at: Optional[str] = None  # ISO8601 带时区；缺失为 None
    ai_generated: bool = False          # 摘要/翻译是否AI生成，默认否（来自源原生）
    lang: str = "zh"                     # 原文语言
    # 热点高亮标记，由 build 阶段启发式判定，不参与去重
    is_hot: bool = field(default=False, compare=False)

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("NewsItem.title 不能为空")
        if not self.original_link or not self.original_link.strip():
            raise ValueError("NewsItem.original_link 不能为空")
        if not self.source or not self.source.strip():
            raise ValueError("NewsItem.source 不能为空")
        if not self.id:
            # 兜底：未传 id 时按链接生成
            self.id = make_id(self.original_link)
        # published_at 不能用 fetched_at 顶替：调用方必须显式传入或留空
        # 此处不做强制，由 fetch 阶段保证语义

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NewsItem":
        # 容忍多余字段，只取已知
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})
