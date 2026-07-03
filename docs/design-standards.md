# 设计规范

> 最后更新：2026-07-03
> 本文档定义代码风格、命名约定和目录结构规范。所有代码必须遵守。

---

## 一、代码风格

### 1.1 语言约定

| 内容 | 使用语言 | 说明 |
|------|----------|------|
| 注释 | **中文** | 方便团队理解业务逻辑 |
| Docstring | **中文** | 模块/类/函数级说明用中文 |
| 变量名 | 英文 | 遵循 snake_case |
| 函数名 | 英文 | 遵循 snake_case |
| 类名 | 英文 | 遵循 PascalCase |
| Git commit | 英文类型 + **中文描述** | 如 `feat: 添加多轮对话 API` |

### 1.2 示例

```python
# ✅ 正确示范
def calculate_profit_margin(revenue: float, cost: float) -> float:
    """计算利润率。返回 (收入 - 成本) / 收入 × 100%。"""
    if revenue == 0:
        return 0.0
    return round((revenue - cost) / revenue * 100, 2)

# ❌ 错误示范（缺注释，变量名无意义）
def calc(a, b):
    return (a - b) / a * 100
```

### 1.3 文件头部模板

```python
"""
模块简短描述（1-2 句话）。

详细说明（如需要）。
"""
```

---

## 二、项目目录结构规范

```
agent-saas/                        # 项目根目录
├── CLAUDE.md                      # Claude Code 工作指引
├── DEVLOG.md                      # 开发日志
├── README.md                      # 项目说明（给 GitHub 访问者看）
├── .env.example                   # 环境变量模板（不含真实密钥）
├── .gitignore                     # Git 忽略规则
├── docker-compose.yml             # Docker 编排文件
├── Dockerfile.backend             # 后端容器构建
├── Dockerfile.frontend            # 前端容器构建
│
├── docs/                          # 📁 项目文档
│   ├── requirements.md            #   需求文档
│   ├── tech-spec.md               #   技术规范
│   ├── design-standards.md        #   设计规范（本文件）
│   └── execution-plan.md          #   执行计划
│
├── backend/                       # 📁 后端服务（FastAPI）
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                #   应用入口
│   │   ├── config.py              #   配置管理
│   │   ├── database.py            #   数据库连接
│   │   ├── models/                #   ORM 模型
│   │   ├── schemas/               #   Pydantic 请求/响应
│   │   ├── routers/               #   API 路由
│   │   ├── services/              #   业务逻辑
│   │   │   └── tools/             #   Agent 工具
│   │   └── utils/                 #   工具函数
│   └── data/                      #   运行时数据（不入 Git）
│
├── frontend/                      # 📁 前端展示（Streamlit）
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                     #   入口
│   ├── pages/                     #   页面模块
│   └── utils/
│       └── api_client.py          #   API 调用封装
│
└── mock_data/                     # 📁 模拟数据
    ├── sample_sales.csv
    └── sample_sop.pdf
```

---

## 三、命名规范速查

| 对象 | 规范 | 示例 |
|------|------|------|
| Python 模块（文件名） | snake_case | `agent_service.py` |
| Python 包（目录名） | 小写无下划线 | `services/` |
| 类名 | PascalCase | `Message`, `ChatRequest` |
| 函数/方法 | snake_case | `send_message()`, `get_sessions()` |
| 常量 | UPPER_SNAKE | `DEFAULT_MODEL_NAME` |
| 数据库表名 | 小写复数 | `sessions`, `messages` |
| API 路径 | kebab-case | `/api/upload/csv` |
| Git 分支 | 类型/功能名 | `feat/chat`, `chore/deploy` |

---

## 四、Git Commit 规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 添加 CSV 上传 API` |
| `fix:` | 修复 Bug | `fix: 修复中文列名解码错误` |
| `docs:` | 文档更新 | `docs: 补充 API 使用说明` |
| `chore:` | 工程配置 | `chore: 初始化 Docker 配置` |
| `refactor:` | 代码重构 | `refactor: 抽取工具注册逻辑` |

---

## 五、安全注意

1. `.env` 文件**绝对不能**提交到 Git（已在 `.gitignore` 中排除）
2. API Key 只能通过环境变量传入，**不能硬编码**在代码里
3. 文件上传限制大小（建议单文件 ≤ 50MB）
4. SQLite 数据库文件不提交到 Git（在 `data/` 目录，已排除）
