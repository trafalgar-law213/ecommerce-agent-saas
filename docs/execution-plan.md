# 执行计划

> 最后更新：2026-07-03
> 本文档定义项目的迭代周期和任务清单。每次开始新周期前必须确认。

---

## 总览

| 周期 | 名称 | 核心产出 | 预计工作量 |
|------|------|----------|------------|
| 0 | 项目脚手架 | Docker Compose 启动，前后端骨架 | 1-2 轮对话 |
| 1 | 核心对话 | 多轮对话 + Agent + Session 持久化 | 2-3 轮对话 |
| 2 | 数据分析 | CSV 上传 → Agent 分析 → 图表 | 2-3 轮对话 |
| 3 | 知识库 RAG | 文档上传 → Chroma 向量化 → 引用式问答 | 2-3 轮对话 |
| 4 | 文案生成 | 多风格营销文案生成工具 | 1 轮对话 |
| 5 | 文档与部署 | README、演示、公网链接 | 2-3 轮对话 |

---

## 第 0 周期：项目脚手架与基础设施

**状态**：🔄 进行中

**Git 分支**：`dev`

**任务清单**：

- [x] Git 初始化 + `.gitignore`
- [x] 项目目录结构
- [x] 后端核心模块（config, database, models, schemas, main）
- [x] 前端骨架（Streamlit 入口 + 三个 Tab 占位）
- [x] 项目文档（CLAUDE.md, docs/, DEVLOG.md）
- [ ] Docker 配置（docker-compose.yml + 两个 Dockerfile）
- [ ] 验证：`docker-compose up` → 前端可访问，`/api/health` 返回 200

**交付物**：能通过 Docker 启动的空框架。

---

## 第 1 周期：核心对话功能

**状态**：⏳ 待开始

**依赖**：第 0 周期完成

**Git 分支**：`feat/chat`（从 `dev` 切出）

**任务清单**：

- [ ] Agent 服务层：LangChain + DeepSeek，纯对话模式
- [ ] POST `/api/chat`：接收消息 → Agent 处理 → 存 DB → 返回
- [ ] GET `/api/sessions`：会话列表
- [ ] GET `/api/sessions/{id}/messages`：消息历史
- [ ] Streamlit 聊天界面：输入框 + 历史消息 + 切换会话
- [ ] 验证：聊天 → 刷新页面 → 历史记录还在

**交付物**：Streamlit 中能与 Agent 多轮对话。

---

## 第 2 周期：CSV 上传与数据分析

**状态**：⏳ 待开始

**依赖**：第 1 周期完成

**Git 分支**：`feat/csv`（从 `dev` 切出）

**任务清单**：

- [ ] CSV 上传 API
- [ ] pandas 数据分析服务
- [ ] `analyze_sales_data` Agent 工具
- [ ] Streamlit 数据分析页面（上传 + 图表展示）
- [ ] 模拟销售数据生成
- [ ] 验证：上传 CSV → 问问题 → 返回分析结果

---

## 第 3 周期：知识库管理与 RAG

**状态**：⏳ 待开始

**依赖**：第 1 周期完成（可与第 2 周期并行）

**Git 分支**：`feat/knowledge`（从 `dev` 切出）

**任务清单**：

- [ ] 文档上传 API（PDF/DOCX/TXT）
- [ ] 文档解析 + 分块 + Chroma 向量存储
- [ ] `search_knowledge_base` Agent 工具
- [ ] Streamlit 知识库管理页面
- [ ] 模拟 SOP 文档生成
- [ ] 验证：上传文档 → 提问 → 引用原文回答

---

## 第 4 周期：文案生成工具

**状态**：⏳ 待开始

**依赖**：第 1 周期完成

**Git 分支**：`feat/copy`（从 `dev` 切出）

**任务清单**：

- [ ] `generate_marketing_copy` Agent 工具
- [ ] 多种风格提示词模板
- [ ] 验证：要求生成文案 → 返回正确风格

---

## 第 5 周期：集成测试、文档与部署

**状态**：⏳ 待开始

**依赖**：第 1-4 周期完成

**Git 分支**：`chore/deploy`（从 `dev` 切出）

**任务清单**：

- [ ] 端到端测试
- [ ] README.md（架构图 + 快速开始 + 截图）
- [ ] Docker 镜像优化
- [ ] GitHub 仓库创建与 push
- [ ] 部署到 Railway/Render
- [ ] 录制演示 GIF
- [ ] `dev` → `main`，打 tag `v1.0.0`

---

## 风险与应对

| 风险 | 可能性 | 应对方案 |
|------|--------|----------|
| DeepSeek API 不稳定 | 低 | 错误处理 + 重试逻辑，提示用户稍后再试 |
| Chroma 持久化问题 | 中 | 确保 volume 正确挂载，数据目录可读写 |
| Streamlit 与 FastAPI 通信失败 | 低 | 健康检查 + 连接失败时前端有明确提示 |
| CSV 编码/格式问题 | 中 | 上传时验证编码，提供错误说明 |
| Docker 构建失败 | 低 | 固定依赖版本，使用多阶段构建 |
