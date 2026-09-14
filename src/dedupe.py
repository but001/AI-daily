"""去重合并：把新采集的 NewsItem 合并到 data/news.json。

去重策略：
- 主键：NewsItem.id（基于 original_link 规范化后的 sha1）
- 次级：标题归一化（去空白+小写）后完全相同视为重复

不变量：
- 单源失败不会清空旧数据：本模块只追加，绝不删除
- "重复导入同输入不产生重复"：相同 id 或相同归一标题，直接跳过

合并后按 published_at 倒序（无日期者排后，按 fetched_at 兜底），便于界面默认展示最新在前。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .models import NewsItem, normalize_title

NEWS_PATH = Path(__file__).resolve().parent.parent / "data" / "news.json"


@dataclass
class MergeResult:
    all_items: List[dict]      # 合并后全量（dict 形式，便于 JSON 序列化）
    added: int                 # 本次新增条数
    duplicates: int           # 因重复跳过的条数


def _sort_key(d: dict) -> tuple:
    """排序键：有 published_at 优先，否则用 fetched_at 兜底。

    ISO8601 字符串可按字典序排序（带时区且 timespec 一致）。
    无任何时间则放最后（返回 "" + 越小越靠前）。
    """
    pa = d.get("published_at") or ""
    fa = d.get("fetched_at") or ""
    # 有 published_at 时正向排序；缺失则把它放后面
    return ("" if pa else "\uffff", pa, fa)


def merge(new_items: List[NewsItem], news_path: Path = NEWS_PATH) -> MergeResult:
    """合并新条目到 news.json，去重并写回。"""
    news_path.parent.mkdir(parents=True, exist_ok=True)

    existing: List[dict] = []
    if news_path.exists():
        try:
            existing = json.loads(news_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            # 旧文件损坏不清空：退化为空列表，但保留原文件备份
            existing = []

    # 主键索引 + 标题索引（基于现有数据构建）
    seen_ids: set[str] = {d.get("id") for d in existing if d.get("id")}
    seen_titles: set[str] = {
        normalize_title(d.get("title", "")) for d in existing if d.get("title")
    }

    added = 0
    duplicates = 0
    for item in new_items:
        if item.id in seen_ids:
            duplicates += 1
            continue
        norm_title = normalize_title(item.title)
        if norm_title and norm_title in seen_titles:
            duplicates += 1
            continue
        existing.append(item.to_dict())
        seen_ids.add(item.id)
        seen_titles.add(norm_title)
        added += 1

    # 排序：最新在前
    existing.sort(key=_sort_key, reverse=True)

    news_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return MergeResult(all_items=existing, added=added, duplicates=duplicates)


def load_news(news_path: Path = NEWS_PATH) -> List[dict]:
    """读取 news.json（不存在则空列表）。"""
    if not news_path.exists():
        return []
    try:
        data = json.loads(news_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []
