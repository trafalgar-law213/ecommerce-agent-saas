# 开发日志（DEVLOG）

> 记录每日/每次对话完成的事项和待办事项。
> 每次对话结束时更新。

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
