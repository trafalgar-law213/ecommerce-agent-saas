# 技术规范

> 最后更新：2026-07-03
> 本文档定义项目的技术选型、数据库设计和 API 约定。开发时作为参考标准。

---

## 一、技术栈

| 层级 | 选型 | 版本 | 选型理由 |
|------|------|------|----------|
| 语言 | Python | 3.11 | 生态成熟，AI/数据类库丰富 |
| 后端框架 | FastAPI | ≥0.110 | 高性能、自动生成 API 文档 |
| 前端 | Streamlit | ≥1.31 | 纯 Python，适合快速做演示 |
| ORM | SQLAlchemy | ≥2.0 | Python 最成熟的 ORM |
| 数据库（开发） | SQLite | — | 零配置，文件即数据库 |
| AI Agent | LangChain | ≥0.3 | ReAct Agent 框架 |
| LLM | DeepSeek | deepseek-chat | OpenAI 兼容格式 |
| 向量数据库 | Chroma | ≥0.5 | 内置持久化，Python 原生 |
| 容器化 | Docker | — | 一键部署 |
| 数据处理 | pandas | ≥2.2 | CSV 分析核心库 |
| 文档解析 | pypdf + python-docx | — | PDF 和 Word 解析 |

---

## 二、数据库设计

### 2.1 表结构速查

**sessions（会话表）**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | String | PK, 默认 uuid[:8] | 会话唯一 ID |
| title | String(200) | 默认"新对话" | 会话标题 |
| created_at | DateTime | 自动填充 | 创建时间 |
| updated_at | DateTime | 自动更新 | 最后活跃时间 |

**messages（消息表）**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, 自增 | 消息 ID |
| session_id | String | FK → sessions.id | 所属会话 |
| role | String(20) | NOT NULL | "user" / "assistant" |
| content | Text | NOT NULL | 消息正文 |
| tool_calls | JSON | 可空 | Agent 工具调用记录 |
| created_at | DateTime | 自动填充 | 发送时间 |

**uploaded_files（上传文件表）**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | String | PK, 默认 uuid[:8] | 文件 ID |
| filename | String(255) | NOT NULL | 原始文件名 |
| file_type | String(20) | NOT NULL | csv/pdf/docx/txt |
| file_path | String(500) | NOT NULL | 服务器存储路径 |
| status | String(20) | 默认"uploaded" | 处理状态 |
| created_at | DateTime | 自动填充 | 上传时间 |

---

## 三、API 设计规范

### 3.1 通用约定

- 所有接口前缀 `/api/`
- 请求体用 JSON，文件上传用 `multipart/form-data`
- 成功响应返回对应 JSON，失败返回 `{"detail": "错误描述"}`
- CORS 开放所有来源（本地开发阶段）

### 3.2 API 清单

| 方法 | 路径 | 说明 | 周期 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | 0 |
| POST | `/api/chat` | 发送消息，返回 Agent 回复 | 1 |
| GET | `/api/sessions` | 会话列表 | 1 |
| GET | `/api/sessions/{id}/messages` | 会话消息历史 | 1 |
| DELETE | `/api/sessions/{id}` | 删除会话 | 1 |
| POST | `/api/upload/csv` | 上传 CSV 文件 | 2 |
| GET | `/api/analysis/{file_id}` | 获取分析结果 | 2 |
| POST | `/api/knowledge/upload` | 上传知识库文档 | 3 |
| GET | `/api/knowledge/search` | 搜索知识库 | 3 |

---

## 四、环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | （必填，无默认值） |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./data/app.db` |
| `UPLOAD_DIR` | 文件上传目录 | `./data/uploads` |
| `CHROMA_DIR` | 向量库目录 | `./data/chroma` |
| `BACKEND_URL` | 后端地址（前端用） | `http://backend:8000` |

---

## 五、Docker 架构

```
docker-compose.yml
├── backend  (FastAPI)
│   ├── 端口: 8000
│   ├── 构建: Dockerfile.backend
│   └── 挂载: ./backend/data → /app/data
└── frontend (Streamlit)
    ├── 端口: 8501
    ├── 构建: Dockerfile.frontend
    ├── 依赖: backend (等待后端启动)
    └── 环境变量: BACKEND_URL=http://backend:8000
```
