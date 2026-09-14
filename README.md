# 每日 AI 情报站

> 让关注 AI 的人，在几分钟内了解近期值得关注的动态。每天自动更新。

每天由 GitHub Actions 在云上定时采集多个独立信息源的 AI 资讯，去重后生成静态站点，部署到 GitHub Pages。无需个人电脑开机，无需服务器，无需付费调用大模型。

## 演示地址

部署到 GitHub Pages 后通过 workflow 自动生成，地址形如：

```
https://<你的GitHub用户名>.github.io/<仓库名>/
```

仓库 Settings → Pages → Source 选 "GitHub Actions" 即可启用。

## 数据来源

| 来源 | 类型 | 语言 | 独立性 |
|---|---|---|---|
| 机器之心 | RSS | 中文 | 国内 AI 媒体 |
| Hugging Face Daily Papers | 公开 API（无密钥） | 英文 | AI 论文社区 |

两个来源是**不同平台的不同入口**（一媒体一学术），满足"至少 2 个独立信息源"要求。新增来源只需在 [config/sources.yaml](config/sources.yaml) 加一条目，并在 [src/sources/](src/sources/) 加同 id 的适配器文件即可。

## 技术选型理由

| 层 | 选型 | 理由 |
|---|---|---|
| 采集 | Python + `feedparser` + `requests` | RSS 解析标准库；HTTP 简单；与构建同语言 |
| 存储 | JSON 文件 | 数据量小（每日几十条），无需数据库；可版本化追溯 |
| 去重 | URL 规范化 sha1 + 标题归一化 | 题目核心验收点"重复导入不产生重复" |
| 静态生成 | Jinja2 | 与采集同语言，无构建链路，易复现 |
| 前端 | 原生 JS + CSS | 数据量小，客户端筛选足够；无框架负担 |
| 定时 | GitHub Actions `schedule` cron | 免费云上定时；不依赖个人电脑 |
| 托管 | GitHub Pages | 零成本静态托管，与源码同仓库 |

整体方案满足题目三条硬约束：**低成本、可复现、不依赖个人电脑开机**。

## 本地运行

需要 Python 3.10+。

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 采集 + 去重 + 构建（一次跑完整流程）
python -m src.main

# 3. 查看站点
#    生成的 _site/index.html 可直接浏览器打开
#    或起本地服务器：
python -m http.server 8000 --directory _site
#    浏览器访问 http://localhost:8000
```

运行测试：

```bash
pip install pytest
python -m pytest tests/ -v
```

仅验证去重/单源失败/缺失字段等逻辑，不依赖网络，14 个测试用例。

## 部署（GitHub Pages）

1. 将仓库推到 GitHub
2. 仓库 Settings → Pages → Source 选 **"GitHub Actions"**
3. 手动触发一次 workflow：Actions 页面 → `daily-update` → "Run workflow"
4. 等待运行结束，Pages URL 会显示在 workflow 总结里

之后每日北京 09:00 自动运行。

## 更新方式

- **定时**：`daily-update.yml` 配置 `cron: '0 1 * * *'`（UTC 01:00 = 北京 09:00），GitHub Actions 云上运行，不依赖本机
- **手动触发**：GitHub Actions 页面 → `daily-update` → "Run workflow"；或命令行：
  ```bash
  gh workflow run daily-update.yml
  ```
- 单源失败：`fetch.py` 内 try/except 捕获，记入 `data/fetch_log.json`，不阻断其他源；界面顶部状态栏标红显示失败源

## 已知限制

- **网络依赖**：采集脚本需访问源站点；GitHub Actions 在国外服务器，访问 HuggingFace、机器之心 RSS 都正常；本地在中国大陆访问 HuggingFace 可能被阻断（用 fixture 测试可绕过）
- **无 AI 摘要**：摘要全部来自源原生 abstract/description，不调用大模型；如未来某源仅提供 AI 生成摘要，会标记 `ai_generated=true` 并在界面显示 "AI 摘要" 徽章
- **去重粒度**：URL 规范化后同一篇文章的不同 utm 参数会归并为一条；以 ID+标题归一化为主键，未做语义级跨事件聚合（题目说明此项不是必做）
- **归档频率**：每日 build 时生成当日快照 `data/archive/<date>.json`；如当天 workflow 触发多次，后一次会覆盖前一次（保留当天最新一份）

## 成本与外部依赖

- **运行成本**：GitHub Actions 公开仓库免费 2000 分钟/月，本项目单次运行约 1-2 分钟；GitHub Pages 公开仓库免费
- **外部依赖**：仅 `feedparser`、`requests`、`Jinja2`、`PyYAML` 四个 Python 包；测试用 `pytest`；无数据库、无大模型 API、无密钥
- **测试成本**：0 元（无付费 API）

## 目录结构

```
.
├── .github/workflows/daily-update.yml   # 定时采集+构建+部署
├── config/sources.yaml                  # 信息源配置
├── data/                                # 数据产物（CI 提交）
│   ├── news.json                        # 累积新闻（追加+去重）
│   ├── fetch_log.json                   # 最近 N 次运行状态
│   └── archive/<date>.json              # 每日快照
├── docs/
│   ├── VERIFICATION.md                  # 验证记录
│   └── DEV_NOTES.md                     # 开发说明
├── src/
│   ├── models.py                        # NewsItem 数据模型
│   ├── fetch.py                         # 采集调度（多源 + 容错）
│   ├── dedupe.py                        # 去重合并
│   ├── build.py                         # 静态构建（含热点 + 归档）
│   ├── main.py                          # 入口
│   └── sources/                         # 各源适配器（一源一文件）
│       ├── jiqizhixin.py                # 机器之心 RSS
│       ├── huggingface_papers.py        # HF Daily Papers API
│       └── _common.py                   # HTTP/HTML清理/时间解析工具
├── static/                              # CSS/JS
├── templates/                           # Jinja2 模板
│   ├── index.html.j2
│   ├── archive.html.j2
│   └── archive_index.html.j2
├── tests/                               # pytest 用例 + fixture
├── requirements.txt
└── README.md
```

## 验证与开发记录

- [验证记录](docs/VERIFICATION.md)
- [开发说明](docs/DEV_NOTES.md)
