"""去重合并测试：核心验证"重复导入同输入不产生重复"。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import NewsItem  # noqa: E402
from src.dedupe import merge, load_news, MergeResult  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "sample_input.json"


def load_fixture_items() -> list[NewsItem]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [NewsItem.from_dict(d) for d in data]


def test_repeat_import_no_duplicates(tmp_path: Path):
    """题目核心验收点：同一份 fixture 连续导入两次，条数不应增长。"""
    news_path = tmp_path / "news.json"

    # 首次导入
    r1: MergeResult = merge(load_fixture_items(), news_path=news_path)
    assert r1.added == 3
    assert r1.duplicates == 0
    assert len(r1.all_items) == 3

    # 第二次导入完全相同输入
    r2: MergeResult = merge(load_fixture_items(), news_path=news_path)
    assert r2.added == 0, "重复导入不应产生新条目"
    assert r2.duplicates == 3, "重复导入应被识别为重复"
    assert len(r2.all_items) == 3, "总数不应增长"


def test_single_source_failure_does_not_clear_old_data(tmp_path: Path):
    """题目验收点：单源失败不清空旧数据。

    模拟：先成功导入 3 条；再次 merge 时传入空列表（模拟单源失败导致 0 条新增），
    旧数据应原样保留。
    """
    news_path = tmp_path / "news.json"
    merge(load_fixture_items(), news_path=news_path)
    before = load_news(news_path)
    assert len(before) == 3

    # 模拟单源失败：本次新增 0 条
    r = merge([], news_path=news_path)
    after = load_news(news_path)
    assert r.added == 0
    assert len(after) == 3, "失败/空导入不应清空旧数据"
    # 旧条目原样保留
    assert {x["id"] for x in after} == {x["id"] for x in before}


def test_url_variant_deduped(tmp_path: Path):
    """同链接的不同 URL 变种应被去重（id 主键去重）。"""
    news_path = tmp_path / "news.json"
    base = {
        "title": "Same article",
        "source": "S",
        "source_url": "",
        "fetched_at": "2026-09-14T00:00:00+00:00",
        "summary": "x",
    }
    a = NewsItem(original_link="https://example.com/article", **base)
    b = NewsItem(original_link="https://example.com/article/", **base)  # 末尾斜杠
    c = NewsItem(original_link="https://example.com/article#top", **base)  # fragment

    r1 = merge([a, b, c], news_path=news_path)
    assert r1.added == 1, "URL 变种应视为同一条"
    assert len(r1.all_items) == 1


def test_same_title_different_url_deduped_by_title(tmp_path: Path):
    """次级去重：标题归一化后相同则视为重复，即使链接不同。"""
    news_path = tmp_path / "news.json"
    items = [
        NewsItem(id="1", title="  GPT-5  发布 ",
                 original_link="https://a/1", source="A", source_url="",
                 fetched_at="2026-09-14T00:00:00+00:00"),
        NewsItem(id="2", title="gpt-5发布",
                 original_link="https://b/2", source="B", source_url="",
                 fetched_at="2026-09-14T00:00:00+00:00"),
    ]
    r = merge(items, news_path=news_path)
    assert r.added == 1, "标题归一化相同应视为重复"
