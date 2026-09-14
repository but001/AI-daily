# 开发说明

## 实际投入时间

约 5 小时（不含写文档）。题目建议上限 8 小时。

## 主要开发工具

- **编辑器**：Trae Code（基于 VS Code）
- **AI 协作**：使用 TRAE（GLM-5.2）作为编程助手，主要承担：
  - 写适配器/模板/测试脚手架
  - 解释 HuggingFace Papers API 字段格式
  - 调试 pytest 失败用例
- **引用的开源项目**：
  - `feedparser`（RSS 解析）
  - `Jinja2`（模板）
  - GitHub Actions 官方 actions：`checkout`、`setup-python`、`configure-pages`、`upload-pages-artifact`、`deploy-pages`
- **未使用任何模板/脚手架项目**：项目结构、CSS、JS 均为自写

## 两个关键决策

### 决策一：静态站点 + GitHub Actions + GitHub Pages，而非前后端服务

**取舍点**：题目允许"定时采集后生成静态页面，或采用完整的前后端服务均可"。

**理由**：
1. 题目硬约束"不依赖用户打开网页或个人电脑持续开机"——GitHub Actions 云上定时天然满足；自建后端则要服务器
2. 题目评分项"工程实现与交付"提到"运行复现"——静态站只需 `python -m src.main` + 静态目录，干净环境复现门槛低；前后端要起服务、配端口、装运行时
3. 数据量小（每天几十条），客户端 JS 筛选足够；不需要后端搜索/分页
4. 零成本：GitHub 公开仓库的 Actions + Pages 都免费，无付费依赖

**代价**：
- 搜索/筛选是客户端做的，数据量大后会卡；本项目数据规模下不构成问题
- 不能做用户级功能（收藏、订阅推送），但题目明确不要求账号/评论

### 决策二：URL 规范化去 query，去 fragment，统一小写

**取舍点**：URL 规范化时是否保留 query？

**理由**：
- 两个源（机器之心 RSS、HF Papers API）的 original_link 都不含 query，所以去 query 不影响生产
- 跨源聚合时，同一篇文章经常以 `?utm_source=xxx`、`?ref=twitter` 等不同 utm 参数出现在多个渠道，去掉 query 才能把它们识别为同一条
- 标题归一化作为次级去重兜底，处理 URL 不同但标题相同的情况（如不同媒体转发同一事件）

**代价**：
- 极少数场景下，源用 `?id=N` 形式的链接会被去重误判；本项目两个源都不属于这种情况，可接受

## 一次问题定位与返工

### 问题：本地端到端构建时 fetch_log.json 显示为空 `{}`

**现象**：用 PowerShell `Out-File -Encoding utf8` 手工构造 `data/fetch_log.json` 后跑 `python -m src.main`，`_site/data/fetch_log.json` 长度只有 2 字节（空对象）。

**定位**：
- 查看 `data/fetch_log.json` 前 3 字节为 `239, 187, 191`（`EF BB BF`，UTF-8 BOM）
- Python `Path.read_text(encoding="utf-8")` 不会跳过 BOM，`json.loads` 抛 `JSONDecodeError`，被 `build.py` 的 `except Exception` 静默吞掉，退化成空字典
- 生产环境里 `fetch.py` 写 fetch_log 用 `json.dumps` + `write_text(encoding="utf-8")`，不会带 BOM；问题只在本地手工构造测试数据时出现

**修复**：
- 用 Write 工具重新生成无 BOM 的 `data/fetch_log.json`，构建即正常
- 不改生产代码：因为生产路径下不会出现 BOM；如果为防御 BOM 而改 `read_text(encoding="utf-8-sig")`，会让代码为几乎不会发生的场景增加复杂度，违背"不为几乎不可能出现的异常编写容错代码"原则

**经验**：本地手工构造的测试数据编码异常很容易被静默吞掉，应在 fixture 写入阶段就用代码生成（用 `json.dumps` + `write_text`），而非编辑器/PowerShell 手写。

## 一次关键取舍：自选亮点为什么做"历史存档 + 每日热点"

题目只要求"一个小而有用的改进"，10 分。最初规划时倾向只做"复制为 Markdown 引用"，理由是写日报/分享时复制粘贴最实在。

**返工点**：在写前端模板时发现列表卡片里已经天然带有"复制为 Markdown 引用"按钮（即只需要在模板里加一个 `<button>` + 一个 JS 函数），实现成本极低，不到 1 个亮点的工作量；于是把它降级为"产品内自带的便利功能"，并补做两个真正解决"使用问题"的小巧思：

1. **离线历史存档**：解决"想回看某天看了什么"的问题——每日 build 时把 `news.json` 拷贝为 `data/archive/<date>.json`，并生成对应静态页。用户从主页可一键跳到任意日期的存档
2. **每日热点 3 条**：解决"几十条看不完，从哪看起"的问题——用关键词加权 + 当日发布加分的启发式打分，标记 top 3 并高亮显示；同源限制最多 1 条，避免单源垄断

**收益**：用户少做了"翻历史找某天文章"和"在几十条里挑重点"两件高成本的事，多获得了"按日期回看"和"3 分钟看完重点"两个能力。
