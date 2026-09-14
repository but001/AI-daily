"""数据模型测试：覆盖缺失字段、超长标题、URL 规范化去重键。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 让测试在项目根目录运行时能 import src
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import NewsItem, make_id, normalize_title, normalize_url  # noqa: E402


FIXTURE = ROOT / "tests" / "fixtures" / "sample_input.json"


def load_fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_missing_published_at_is_none():
    """缺失发布时间：published_at 应为 None，不编造、不冒充。"""
    items = load_fixture()
    missing = [x for x in items if x["published_at"] is None][0]
    ni = NewsItem(**missing)
    assert ni.published_at is None


def test_long_title_preserved():
    """超长标题：原样保留，由前端负责换行处理。"""
    items = load_fixture()
    long_item = [x for x in items if "long" in x["id"]][0]
    ni = NewsItem(**long_item)
    assert ni.title == long_item["title"]
    assert len(ni.title) > 80


def test_required_fields_raise_on_empty():
    """必要字段缺失应抛错（不在模型层静默兜底）。"""
    with pytest.raises(ValueError):
        NewsItem(id="x", title="", original_link="https://a.b/c",
                 source="S", source_url="", fetched_at="")
    with pytest.raises(ValueError):
        NewsItem(id="x", title="t", original_link="",
                 source="S", source_url="", fetched_at="")
    with pytest.raises(ValueError):
        NewsItem(id="x", title="t", original_link="https://a.b/c",
                 source="", source_url="", fetched_at="")


def test_normalize_url_strips_query_fragment_and_slash():
    """URL 规范化：去 fragment、统一大小写、去末尾斜杠。"""
    a = normalize_url("HTTPS://Example.com/path/?utm_source=x#top")
    b = normalize_url("https://example.com/path")
    assert a == b


def test_make_id_stable_across_url_variants():
    """同链接不同变种应生成同 id（去重前提）。"""
    id1 = make_id("https://example.com/article/")
    id2 = make_id("https://example.com/article")
    id3 = make_id("https://example.com/article#section")
    assert id1 == id2 == id3


def test_normalize_title_ignores_whitespace_and_case():
    a = normalize_title("  Hello World  ")
    b = normalize_title("helloworld")
    assert a == b


def test_from_dict_tolerates_extra_fields():
    """老数据有新字段不影响反序列化；多余字段被忽略。"""
    ni = NewsItem.from_dict({
        "id": "abc", "title": "T", "original_link": "https://a.b/c",
        "source": "S", "source_url": "", "fetched_at": "2026-09-14T00:00:00+00:00",
        "extra_field_unknown": 123,
    })
    assert ni.id == "abc"
