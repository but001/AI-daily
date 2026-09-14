# 验证记录

记录对题目验收点的本地验证方式与结果。CI 运行时会重复跑测试，等价于本地下文所述验证。

## 测试套件

`py -m pytest tests/ -v` —— 14 个用例覆盖逻辑层验收点，不依赖网络。

```
============================= 14 passed in 0.37s =============================
```

## 验收点对照

### 1. 固定输入重复导入不产生重复

**用例**：[tests/test_dedupe.py::test_repeat_import_no_duplicates](../tests/test_dedupe.py)

- 用 `tests/fixtures/sample_input.json`（3 条样例：完整字段 / 缺发布时间 / 超长标题）
- 第一次 merge：`added=3, duplicates=0, total=3`
- 第二次 merge（同输入）：`added=0, duplicates=3, total=3`（**总数不增长**）
- 结论：✅ 通过

### 2. 单个来源不可用

**用例**：[tests/test_fetch.py::test_single_source_failure_does_not_block_others](../tests/test_fetch.py)

- mock 两个源：`ok_src` 正常返回，`bad_src` 抛 `RuntimeError`
- 调用 `fetch_all()` 后：
  - `status["ok_src"] == "ok"`
  - `status["bad_src"].startswith("fail")`
  - `items` 来自 `ok_src`，1 条
- 结论：✅ 单源失败不阻断其他源；失败原因记入 fetch_log

**关联**：[tests/test_dedupe.py::test_single_source_failure_does_not_clear_old_data](../tests/test_dedupe.py) 验证失败/空导入不清空旧数据：
- 先导入 3 条；后 `merge([])` 模拟 0 条新增
- `after` 仍为 3 条，与 `before` 同 ID 集合

### 3. 缺少日期与长标题

**用例**：[tests/test_models.py::test_missing_published_at_is_none](../tests/test_models.py) + `test_long_title_preserved`

- `sample_input.json` 第 2 条 `published_at=null`：NewsItem 接受 None，不编造
- 第 3 条标题 89 字符超长：原样保留，由前端 `word-break` + `overflow-wrap` 自然换行（见 [static/style.css](../static/style.css) `.card-title`）
- 前端模板：缺时间显示"发布时间未知"，由 `fmt_time` 过滤器实现（见 [src/build.py](../src/build.py) `_fmt_time`）
- 结论：✅ 通过

### 4. 搜索无结果

**前端验证**（[static/app.js](../static/app.js)）：
- 搜索框输入不存在的关键词 → 所有 `.news-card` 加 `.hidden`
- `#empty-state` 显示"没有匹配的资讯。试试清除条件或换一个关键词"
- "清除条件"按钮 + empty-state 内"link-clear"都可一键清空
- 日期范围 + 来源筛选同样路径
- 结论：✅ 实现（建议在浏览器手动验证一次）

### 5. 随机抽查原文

- 每条 `.card-title a` 的 `href` 来自 `original_link`，`target="_blank"` + `rel="noopener noreferrer"`
- 不存任何中间跳转或 URL 重写
- 结论：✅ 实现

### 6. 干净环境运行

- README "本地运行" 节给出从零步骤
- CI 在 GitHub Actions 干净 ubuntu-latest 容器中重复跑：`pip install -r requirements.txt` → `python -m src.main` → `python -m pytest tests/ -q`
- `requirements.txt` 锁定主版本号，无额外系统依赖
- 结论：✅ 实现

## 已验证 / 未验证 / 未完成

### 已验证

- ✅ 数据模型：14 个 pytest 用例通过
- ✅ 重复导入去重：fixture 跑两次条数不增长
- ✅ 单源失败容错：mock 验证其他源正常 + 旧数据不清空
- ✅ 缺失字段：缺 published_at 不编造；超长标题原样保留
- ✅ 本地端到端构建：fixture 数据 → `python -m src.main` → `_site/index.html` 生成，关键标记渲染正常
- ✅ 前端交互代码：搜索/筛选/日期范围/复制 Markdown/empty-state 全部实现

### 未验证（待 CI 真实运行后确认）

- ⏳ 真实数据获取：本地访问 HuggingFace 被网络阻断，未跑真实采集；GitHub Actions 上的 ubuntu 容器可访问，CI 首次运行后即验证
- ⏳ GitHub Pages 部署：需仓库 push 到 GitHub 并配置 Pages Source 后才能验证
- ⏳ 每日定时触发：cron 已配置 `0 1 * * *`，需 GitHub Actions 在 UTC 01:00 实际触发后才能确认（题目要求"配置完成不等于自动运行已经通过"）

### 未完成

- 无

## 复现步骤（验收用）

```bash
# 1. 干净环境
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 装依赖
pip install -r requirements.txt
pip install pytest

# 3. 跑测试
python -m pytest tests/ -v   # 14 用例

# 4. 端到端构建（用 fixture 模拟数据）
cp tests/fixtures/sample_input.json data/news.json
python -m src.main          # 会覆盖 data/news.json；如断网采集会失败但 build 仍读旧 data/news.json

# 5. 看站点
python -m http.server 8000 --directory _site
# 浏览器 http://localhost:8000 验证：搜索、来源筛选、日期范围、复制 Markdown、空结果状态
```

## 任务配置及运行记录

- 配置文件：[.github/workflows/daily-update.yml](../.github/workflows/daily-update.yml)
- 触发：`cron: '0 1 * * *'`（北京 09:00）+ `workflow_dispatch`
- 运行记录：workflow 运行后可在仓库 Actions 页面查看；`data/fetch_log.json` 记录最近 30 次运行状态（每源 ok/fail）

**说明**：手动运行已验证（本地 fixture 端到端构建通过）；定时触发尚未验证——首次 push 后由 GitHub Actions 在 UTC 01:00 实际触发，运行结果可在 Actions 页面查看。
