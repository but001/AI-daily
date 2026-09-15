# 📰 AI-daily (每日 AI 情报站)

<div align="center">

![AI-daily](https://img.shields.io/badge/AI--daily-每日情报站-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![CI/CD](https://img.shields.io/badge/CI/CD-GitHub%20Actions-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**全自动化的 AI 资讯聚合站，零服务器成本，每天北京时间 09:00 自动更新。**

在线演示：https://but001.github.io/AI-daily/ · 问题反馈：https://github.com/but001/AI-daily/issues

</div>

## 📖 项目简介

**AI-daily** 是一个基于 GitHub Actions 和 GitHub Pages 构建的自动化 AI 资讯情报站。它在云端定时抓取全球多个独立 AI 资讯源，经过去重、60 天保留窗口淘汰后，使用 Jinja2 模板渲染为静态网页部署到 GitHub Pages。

**无需购买服务器，无需人工干预，真正实现"采集-清洗-建站-部署"全链路自动化。**

## 🛠 技术栈

- **核心语言**: Python 3.10+
- **数据抓取**: `feedparser` (RSS/Atom 解析), `requests` (HTTP)
- **数据处理与配置**: `PyYAML` (YAML 配置)
- **前端渲染**: `Jinja2` (HTML 模板)
- **前端交互**: 原生 JavaScript（搜索/筛选/阅读记录，无框架依赖）
- **自动化与部署**: GitHub Actions + GitHub Pages

## ✨ 核心特性

- **🕒 每日定时更新**：GitHub Actions cron（UTC 01:00 / 北京时间 09:00）自动采集最新资讯。
- **🌐 多渠道聚合**：已接入 OpenAI Blog、TechCrunch AI、Hugging Face Blog、Hacker News AI、ArXiv cs.AI 共 5 个独立信息源。
- **🧹 智能去重与保留**：基于链接 SHA1 + 标题归一化双重去重；60 天数据保留窗口淘汰过期条目，避免数据无限增长。
- **⚡ 静态站点生成**：Jinja2 渲染 JSON 数据为静态网页，GitHub Pages 极速分发。
- **🔍 全功能前端筛选**：关键词搜索、来源筛选、日期段选择（今天/近7天/近30天/自定义起止日期），搜索时实时显示匹配数量。
- **📚 本地阅读记录**：基于 localStorage 记录用户点开过的文章，独立"我的阅读"页面查看。
- **🛠 多种触发方式**：定时 cron + push 自动部署 + workflow_dispatch 手动触发。
- **📦 数据回写归档**：每日采集结果自动 commit 回仓库（data/news.json + data/fetch_log.json），方便回溯与二次开发。
- **🧪 测试覆盖**：14 个 pytest 用例覆盖模型、去重、采集调度容错三大模块。

## 📂 项目结构

```text
AI-daily/
├── .github/workflows/
│   └── daily-update.yml        # GitHub Actions 自动化工作流
├── config/
│   └── sources.yaml            # 信息源配置（可自由扩展）
├── src/
│   ├── main.py                 # 编排入口：采集→去重→构建一次跑完
│   ├── fetch.py                # 采集调度：加载配置→路由适配器→容错汇总
│   ├── dedupe.py               # 去重合并 + 60天保留窗口
│   ├── build.py                # Jinja2 静态站点构建
│   ├── models.py               # NewsItem 数据模型
│   └── sources/                # 各源适配器
│       ├── _common.py          # 共用工具：HTTP、时间解析、HTML 清洗
│       ├── rss.py              # 通用 RSS 2.0/Atom 适配器（4 个源共用）
│       └── arxiv.py            # ArXiv API 专用适配器
├── templates/                  # Jinja2 HTML 模板
│   ├── index.html.j2           # 今日主页（搜索/筛选/今日热点）
│   └── my-reading.html.j2      # 我的阅读（localStorage 阅读记录）
├── static/
│   ├── app.js                  # 前端交互：搜索/筛选/日期弹窗/阅读记录
│   └── style.css               # 响应式样式
├── tests/                      # pytest 测试套件
│   ├── test_models.py
│   ├── test_dedupe.py
│   ├── test_fetch.py
│   └── fixtures/sample_input.json
├── data/
│   ├── news.json               # 资讯数据（自动生成）
│   └── fetch_log.json          # 采集运行日志（自动生成）
├── docs/
│   ├── DEV_NOTES.md            # 开发说明（关键决策与取舍）
│   └── VERIFICATION.md         # 验证记录
├── requirements.txt
└── README.md
```

## ⚙ 自动化工作流原理解析

每天 `.github/workflows/daily-update.yml` 会在云端执行：

1. **环境准备**：拉取代码，配置 Python 3.10+，安装 `requirements.txt` 依赖。
2. **采集**：`src/main.py` 调用 `src/fetch.py`，按 `config/sources.yaml` 路由到各源适配器获取最新条目。单源失败不阻断其他源。
3. **去重与淘汰**：`src/dedupe.py` 合并新条目到 `data/news.json`，基于 id + 归一标题双重去重，并淘汰超过 60 天的旧条目。
4. **测试**：运行 `pytest tests/ -q` 验证产物完整性。
5. **构建**：`src/build.py` 用 Jinja2 渲染 `data/news.json` 为静态站点到 `_site/`。
6. **数据回写**：把更新后的 `data/news.json` + `data/fetch_log.json` commit 回 main 分支。
7. **部署**：把 `_site/` 部署到 GitHub Pages。

触发条件：
- 定时：`cron: '0 1 * * *'`（每天 UTC 01:00 / 北京时间 09:00）
- 代码推送：`src/`、`templates/`、`static/`、`config/` 变更时自动触发全流程
- 手动：GitHub Actions 页面点 "Run workflow"

## 🚀 快速开始（本地开发）

### 1. 克隆仓库
```bash
git clone https://github.com/but001/AI-daily.git
cd AI-daily
```

### 2. 创建虚拟环境并安装依赖
```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置信息源
编辑 `config/sources.yaml`，可添加或修改 RSS/API 源：
```yaml
sources:
  - id: openai
    name: OpenAI Blog
    adapter: rss              # 用通用 RSS 适配器
    url: https://openai.com/news/rss.xml
    lang: en
    homepage: https://openai.com/news
    enabled: true

  - id: arxiv
    name: arXiv cs.AI
    type: api                 # 用专用 arxiv 适配器（按 id 路由）
    url: http://export.arxiv.org/api/query
    lang: en
    homepage: https://arxiv.org/list/cs.AI/recent
    enabled: true
```

### 4. 一键运行（采集 + 去重 + 构建）
```bash
python src/main.py
```

或者分步执行：
```bash
# 仅采集
python -c "from src.fetch import fetch_all; fetch_all()"

# 仅去重合并
python -c "from src.dedupe import load_news; load_news()"

# 仅构建
python -c "from src.build import main; main()"
```

构建产物在 `_site/` 目录，浏览器打开 `_site/index.html` 即可预览。

### 5. 运行测试
```bash
python -m pytest tests/ -q
```

## 🔌 扩展信息源

新增一个 RSS 源只需 3 步：

1. 在 `config/sources.yaml` 加一条，`adapter: rss` 用通用适配器：
   ```yaml
   - id: my_source
     name: My AI Source
     adapter: rss
     url: https://example.com/rss
     lang: en
     homepage: https://example.com
     enabled: true
   ```

2. 如果是特殊 API（非标准 RSS/Atom），在 `src/sources/` 新建同名 `.py` 文件实现 `fetch(config)` 返回 `List[NewsItem]`。配置里不写 `adapter`，会按 `id` 路由。

3. 提交推送，CI 自动跑一次全流程验证。

## 📊 数据来源

| 来源 | 类型 | 语言 | 说明 |
|---|---|---|---|
| OpenAI Blog | RSS | 英文 | 一手信源，AI 前沿动态 |
| TechCrunch AI | RSS | 英文 | 行业媒体，覆盖面广 |
| Hugging Face Blog | RSS | 英文 | 开源社区动态 |
| Hacker News AI | RSS | 英文 | 开发者讨论热点 |
| arXiv cs.AI | API（Atom） | 英文 | 学术论文预印本 |

5 个源均为**不同平台的不同入口**，满足"至少 2 个独立信息源"要求。

## 🧠 关键设计决策

详细见 [docs/DEV_NOTES.md](docs/DEV_NOTES.md)。摘要：

- **纯静态站点**：Jinja2 + 原生 JS，无后端框架，GitHub Pages 零成本托管。
- **单源失败容错**：fetch.py try/except 包住每个源，失败记入 fetch_log 不阻断其他源，旧数据不被清空。
- **60 天保留窗口**：dedupe.py 每次合并淘汰过期条目，避免 news.json 无限增长。
- **日期段交互**：主按钮组覆盖 90% 场景（今天/近7天/近30天），自定义弹窗覆盖 10% 场景，移动端友好。
- **阅读记录用 localStorage**：零后端成本、隐私友好（数据不出本机），限制是不跨设备同步——这是设计取舍。

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request！
1. Fork 本仓库
2. 新建分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加新源'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 开源协议

本项目采用 [MIT](LICENSE) 协议。

---

*如果这个项目对你有帮助，欢迎点个 ⭐️ Star 支持一下！*
