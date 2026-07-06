# 开发日志（DEVLOG）

> 记录每日/每次对话完成的事项和待办事项。
> 每次对话结束时更新。

---

## 2026-07-06 — 第 7 周期：Agent 可观测性与流式输出

### 完成事项

- [x] AgentTrace 数据模型 — 记录每次 Agent 调用的耗时、工具列表、Token 消耗、轮次、状态
- [x] AgentService 增加 `run_stream()` 流式方法 — 支持 SSE 事件推送（text / tool_start / tool_end / done / error）
- [x] AgentService 增加指标追踪 — `time.perf_counter()` 计时 + `response_metadata` token 提取
- [x] 新增 `POST /api/chat/stream` 流式对话端点 — SSE 格式，数据库在流结束后写入
- [x] 新增 `GET /api/observability/traces` — 追踪记录列表（分页、倒序）
- [x] 新增 `GET /api/observability/stats` — 聚合统计（成功率、平均耗时、Token 总量、工具分布）
- [x] 前端对话助手改用流式 API — `send_message_stream()` + 实时文本显示 + 工具调用进度
- [x] 前端新增"🔍 可观测性"Tab — 统计卡片（4 指标 + 2 指标）+ 工具分布柱状图 + 调用记录表
- [x] 非流式 `/api/chat` 同步增加 trace 记录（向后兼容）
- [x] 端到端验证：流式文本 → 工具调用进度 → 追踪记录 → 聚合统计 全链路通过
- [x] SQLite JSON 字段兼容处理（token_usage 统计改用 Python 遍历）

### 当前状态

- 项目 7 个迭代周期
- 28 个 conventional commits

---

## 2026-07-05 — 第 6 周期：Bug 修复、性能优化与收尾

### 完成事项

- [x] 知识库同名文件去重（上传前检查，409 Conflict）
- [x] 知识库删除端点重写（同时清理 Chroma + DB + 磁盘文件）
- [x] Chroma 管理操作跳过嵌入模型加载（count/list/delete 毫秒级响应）
- [x] 知识库搜索增加 AI 合成回答（synthesize=true 参数）
- [x] Agent 知识库工具返回格式优化（指示 LLM 整合而非逐条复述）
- [x] 前端侧边栏去重（pages/ → tabs/，消除 Streamlit 自动生成的冗余导航）
- [x] 分析页 Enter 键支持（改用 st.form + form_submit_button）
- [x] 分析结果完整展示（修复数据表格从未渲染的 Bug）
- [x] 分析关键词匹配增强（支持"卖得最好""销量最高""赚钱"等自然语言）
- [x] 分析结果展示汇总行数（让用户清楚数据是加总后的结果）
- [x] RAG 服务错误日志完善（不再吞异常）
- [x] 前端删除按钮 key 冲突修复

### 项目完结

- 24 个 conventional commits，Git 历史清晰
- 三大核心功能全链路验证通过
- 准备推送到 GitHub 公开仓库

---

## 2026-07-05 — 第 5 周期：文档、Docker 与收尾

### 完成事项

- [x] `README.md` — 完整项目文档
  - 徽章行（Python / FastAPI / Streamlit / LangChain / Docker / License）
  - 项目背景与痛点描述
  - Mermaid 架构图
  - 核心功能一览表（3 个 Agent 工具 + 触发词）
  - 快速开始（本地运行 + Docker 部署）
  - 完整项目目录结构注释
  - 技术栈与选型理由表
  - 未来规划
- [x] `LICENSE` — MIT License
- [x] `docker-compose.yml` 优化：
  - 移除过时的 `version` 字段
  - 添加 `hf-cache` 命名卷（HuggingFace 模型缓存持久化）
  - 修复 M3E_MODEL_PATH 默认值（空值 → 自动从 HF 镜像下载）
- [x] `start.bat` — Windows 一键启动脚本（自动找端口 + 启动前后端）
- [x] 修复 bugs：
  - 前端 analysis.py 中文引号与 Python 字符串冲突
  - api_client.py BACKEND_URL 尾部空格导致连接失败
- [x] Git commit：`docs: 添加 README、LICENSE 与 Docker 配置优化` + 前置修复提交

### 当前状态

- 项目 6 个迭代周期全部完成 ✅
- Agent 集成 3 个工具，全链路验证通过
- README 文档完善，可直接用于 GitHub 公开仓库
- Docker 配置优化，支持一键部署
- Git 提交历史清晰（17 个 conventional commits）

### 待办（发布前检查清单）

- [ ] 在 GitHub 创建公开仓库并推送
- [ ] 仓库 About 栏填写 + Topics 标签设置
- [ ] （可选）录制演示 GIF
- [ ] （可选）部署到 Railway / Render 获取公网链接

---

## 2026-07-03 — 第 4 周期：营销文案生成工具

### 完成事项

- [x] `backend/app/services/tools/copy_tools.py` — Agent 文案生成工具
  - `@tool generate_marketing_copy(product_info, style, channel)` — 3 种风格 × 3 种渠道
  - 风格：活泼（emoji + 网感）、专业（参数 + 背书）、简洁（短句 + 高密度）
  - 渠道：小红书（种草体 + 话题标签）、朋友圈（日常分享体）、详情页（卖点 bullet points）
  - 工具内独立 ChatOpenAI 实例（temperature=0.85，增强创意）
  - 严格的提示词模板：不编造卖点、直接输出文案正文
- [x] Agent 工具注册：`_auto_register_tools()` 新增 generate_marketing_copy
- [x] 实测验证：
  - 输入"给 299 元无线降噪蓝牙耳机写小红书种草文案"
  - Agent 自动调用 generate_marketing_copy → 输出高质量小红书文案（标题 + 正文 + emoji + 场景痛点）
- [x] Git commit：`feat: 添加 generate_marketing_copy 文案生成工具`（3 文件，+113 行）

### 当前状态

- Agent 集成 3 个工具：analyze_sales_data + search_knowledge_base + generate_marketing_copy
- 项目已完成第 0/1/2/3/4 周期（共 6 周期），核心功能齐备

### 下一步计划

- **第 5 周期**：集成测试、文档完善、Docker 验证、GitHub 推送

---

## 2026-07-03 — 第 3 周期：知识库管理与 RAG

### 完成事项

- [x] `backend/app/services/rag_service.py` — RAG 知识库检索服务
  - 文档解析：PDF（pypdf）、DOCX（python-docx）、TXT（含编码检测）
  - 文本分块：RecursiveCharacterTextSplitter（chunk_size=500, overlap=50）
  - 向量嵌入：moka-ai/m3e-base（768 维中文模型，通过 hf-mirror.com 镜像或本地路径加载）
  - 存储：Chroma 向量库持久化到 `data/chroma/`
  - 检索：`search(query, top_k)` 返回相似度分数 + 来源文档
  - 管理：`get_document_count()` / `get_document_sources()` / `delete_document()`
- [x] `backend/app/services/tools/kb_tools.py` — Agent 知识库检索工具
  - `@tool search_knowledge_base(query)` — 当用户咨询运营 SOP/客服话术/流程规范时自动调用
  - 自动判断知识库是否为空，空库时提示上传
- [x] 知识库 API 端点（`backend/app/routers/upload.py`）：
  - POST /api/knowledge/upload — 上传文档（PDF/DOCX/TXT，20MB 限制）
  - GET /api/knowledge/search?q=&top_k= — 语义搜索知识库
  - GET /api/knowledge/documents — 已上传文档列表
- [x] `backend/app/schemas/upload.py` — 新增 KnowledgeUploadResponse、KnowledgeDocumentItem
- [x] Agent 工具注册：`_auto_register_tools()` 新增 search_knowledge_base
- [x] `mock_data/sample_sop.txt` — 模拟电商运营 SOP 知识库（退货流程/客服话术/发货规范/选品规则/会员体系等 7 章）
- [x] `frontend/pages/knowledge.py` — 重写知识库管理页面
  - 文档上传（PDF/DOCX/TXT 批量上传 + 处理进度）
  - 已上传文档列表展示
  - 语义搜索测试区（输入问题 → 展示检索结果 + 相关度）
- [x] `frontend/utils/api_client.py` — 新增 `get_knowledge_documents()`
- [x] 嵌入模型选型解决：
  - 初始 `paraphrase-multilingual-MiniLM-L12-v2` → HuggingFace 连接超时
  - 切换 `moka-ai/m3e-base` + hf-mirror.com 镜像下载成功
  - 支持 `M3E_MODEL_PATH` 环境变量直接加载本地模型
- [x] 全链路验证：
  - 上传 sample_sop.txt → 分块 10 段 → 向量化存入 Chroma ✅
  - 搜索"退货流程" → 返回 3 条相关结果（最高相关度 76%）✅
  - Agent 对话"退货流程是什么？" → 自动调用 search_knowledge_base 工具 → 生成结构化回答（表格 + 特殊场景提醒）✅
- [x] Git commit：`feat: 添加知识库 RAG 系统（Chroma 向量检索 + m3e-base 嵌入 + 文档解析）`（12 文件，+775 行）

### 当前状态

- 后端启动正常（uvicorn :8000/8001）
- Agent 集成 2 个工具：analyze_sales_data（CSV）+ search_knowledge_base（知识库）
- 项目已完成第 0/1/2/3 周期（共 6 周期），可运行

### 下一步计划

- **第 4 周期**：营销文案生成工具（generate_marketing_copy）

---

## 2026-07-03 — 第 2 周期：CSV 上传与数据分析

### 完成事项

- [x] `backend/app/services/csv_service.py` — pandas 数据分析服务
  - 支持自然语言查询：Top N 排名、利润率、趋势、分类汇总、概览
  - 自动识别列名（商品名称/销售额/成本/日期/分类等）
  - `_to_native()` 递归转换 numpy 类型，确保 JSON 可序列化
- [x] `backend/app/routers/upload.py` — 文件上传与 API 路由
  - POST /api/upload/csv — CSV 上传（10MB 限制，自动解析验证）
  - POST /api/upload/csv/{id}/analyze — 自然语言分析查询
  - GET /api/analysis/{file_id} — 文件基本信息
- [x] `backend/app/services/tools/csv_tools.py` — Agent CSV 分析工具
  - `@tool analyze_sales_data(query)` — 自动查找最新上传的 CSV 并分析
  - 工具内独立数据库会话，不依赖 FastAPI Depends
- [x] Agent 工具调用机制升级：
  - `_auto_register_tools()` — 自动注册可用的工具模块
  - `_run_with_tools()` — 改用 `bind_tools` + tool calling 循环（取代 hub.pull ReAct）
  - 完整对话上下文保留，LLM 自主判断是否调用工具
- [x] `mock_data/sample_sales.csv` — 模拟电商销售数据（834 行 × 60 天 × 20 商品 × 4 分类）
- [x] `frontend/pages/analysis.py` — 重写数据分析页面
  - 文件上传 + 解析预览
  - 自然语言查询输入 + 分析结果展示
  - 图表渲染（bar_chart / line_chart）
- [x] `frontend/utils/api_client.py` — 新增 `analyze_csv()` 函数
- [x] 修复 Bug：
  - pandas numpy 类型无法 JSON 序列化 → `_to_native()` 转换
  - AnalysisResponse 不能接收 list 类型 → `Union[dict, list]`
  - data/ 目录被追踪 → 加入 .gitignore
- [x] 验证全链路：上传 CSV → API 分析 → Agent 工具调用 → 前端展示
- [x] Agent 实战测试：输入"帮我分析 Top 5 商品"，Agent 自动调用 analyze_sales_data 工具并返回格式化表格
- [x] Git commit：`feat: 添加 CSV 上传 API、pandas 数据分析服务与 Agent 工具`（11 文件，+1787 行）

### 当前状态

- 后端启动正常（uvicorn :8000）
- 前端连接正常（🟢 后端已连接）
- Agent 工具调用循环正常（bind_tools → 工具执行 → 结果回传 → 最终回复）
- 项目已完成第 0/1/2 周期（共 6 周期），可运行

### 下一步计划

- **第 3 周期**：知识库管理与 RAG（Chroma 向量检索 + 文档解析）
