"""每日更新入口：采集 → 去重合并 → 构建静态站点。

供 GitHub Actions workflow 调用，也可本地手动运行验证：
    py -m src.main

输出：data/news.json 增量、_site/ 静态站。
"""
from __future__ import annotations

import sys

from . import fetch as fetch_mod
from . import dedupe as dedupe_mod
from . import build as build_mod


def main() -> int:
    # 1. 采集（单源失败被 fetch 内部捕获，不阻断）
    result = fetch_mod.fetch_all()
    print(f"[fetch] 采集到 {len(result.items)} 条新条目", file=sys.stderr)
    for sid, st in result.status.items():
        print(f"  - {sid}: {st}", file=sys.stderr)

    # 2. 去重合并到 data/news.json（失败/空导入不清空旧数据）
    merge_result = dedupe_mod.merge(result.items)
    print(
        f"[dedupe] 新增 {merge_result.added}，重复 {merge_result.duplicates}，"
        f"总量 {len(merge_result.all_items)}",
        file=sys.stderr,
    )

    # 3. 构建静态站点（含当日归档快照 + 历史归档页）
    build_mod.build_all()
    print("[build] 站点已生成到 _site/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
