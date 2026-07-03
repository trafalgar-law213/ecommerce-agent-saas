# CLAUDE.md

> 本文件是 Claude Code 的项目指引。Claude 会在每次对话开始时读取此文件，了解项目规范和标准文件位置。

---

## 项目简介

**电商智能客服与选品助手 Agent SaaS** — 帮助中小电商团队用自然语言分析销售数据、生成营销文案、基于内部 SOP 知识库回答运营问题。

## 标准文件索引

本项目所有开发和设计规范集中存放在 `docs/` 目录。开始任何开发任务前，请先查阅对应的标准文件：

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [docs/requirements.md](docs/requirements.md) | 项目需求文档 — 业务目标、用户故事、功能描述 | 理解"要做什么"时 |
| [docs/tech-spec.md](docs/tech-spec.md) | 技术规范 — 技术栈版本、数据库设计、API 约定 | 写代码前参考技术选型 |
| [docs/design-standards.md](docs/design-standards.md) | 设计规范 — 代码风格、命名约定、目录结构 | 不确定"怎么写"时 |
| [docs/execution-plan.md](docs/execution-plan.md) | 执行计划 — 迭代周期、任务清单、依赖关系 | 规划下一步工作时 |
| [DEVLOG.md](DEVLOG.md) | 开发日志 — 每日完成事项和待办记录 | 记录进度时 |

## 工作约定

### 开发节奏

1. **小步快跑**：每个迭代周期拆分为多个独立任务，每完成一个任务就做 Git commit
2. **先确认再动手**：每次执行新周期前，先告知用户计划，确认后再写代码
3. **及时记录**：每天/每次对话结束时，更新 `DEVLOG.md`

### Git 规范

- 分支策略：`main ← dev ← feat/功能名`
- Commit 格式：`feat:` / `fix:` / `docs:` / `chore:` / `refactor:` + 中文描述
- 每个功能分支合并后及时删除

### 代码风格

- 所有注释和文档用中文（方便团队理解）
- 变量/函数/类名用英文
- 每个 `.py` 文件必须包含模块级 docstring
- 公共函数必须包含参数说明

### 验证约定

- 写完代码后必须验证能否启动：`docker-compose up --build`
- 新增 API 端点必须在 Streamlit 页面能调通
- 不允许有 `pass` 留在已实现的功能里

## 技术栈速查

```
Python 3.11  ·  FastAPI  ·  Streamlit  ·  SQLAlchemy  ·  SQLite
LangChain  ·  Chroma  ·  Docker  ·  DeepSeek API (OpenAI 兼容)
```
