"""
LangChain Agent 服务层。

封装 DeepSeek LLM 调用和 Agent 工具管理。
第 1 周期：纯对话模式（无工具）。
后续周期逐步注册 CSV 分析、知识库检索、文案生成等工具。
"""

from typing import Optional, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# ── System Prompt ──────────────────────────────────────────────
# 定义 Agent 的行为边界和能力描述

SYSTEM_PROMPT = """你是一个专业的电商智能客服与选品助手。

你的能力范围：
1. 销售数据分析 — 帮助用户分析 CSV 销售数据，计算 Top N、利润率、趋势等
2. 营销文案生成 — 根据商品信息生成小红书、朋友圈、详情页等风格的推广文案
3. 运营知识问答 — 基于上传的 SOP 知识库回答退货流程、客服话术等问题

回答原则：
- 如果用户的问题超出你的能力范围，诚实告知并建议合适的解决方向
- 优先使用工具获取准确数据，而非猜测
- 回答简洁有条理，关键信息用列表呈现
- 分析类问题给出具体数字和结论，不要只描述方法
- 用中文回答，语气友好专业"""


class AgentService:
    """电商智能客服 Agent。

    封装 LLM 调用，管理工具注册和消息历史。
    """

    def __init__(self):
        self._llm: Optional[ChatOpenAI] = None
        self._tools: List = []
        self._system_prompt = SYSTEM_PROMPT
        self._auto_register_tools()

    @property
    def llm(self) -> ChatOpenAI:
        """延迟初始化 LLM 实例（避免在模块导入时就连接 API）。"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.7,
                max_tokens=2048,
            )
        return self._llm

    def register_tools(self, tools: list):
        """注册 Agent 工具（第 2-4 周期使用）。

        Args:
            tools: LangChain @tool 装饰的函数列表
        """
        self._tools.extend(tools)

    def _auto_register_tools(self):
        """自动注册可用的 Agent 工具。

        各周期逐步添加工具，如果工具依赖的库/文件不可用则跳过。
        """
        # CSV 数据分析工具（第 2 周期）
        try:
            from .tools.csv_tools import analyze_sales_data
            self._tools.append(analyze_sales_data)
        except ImportError:
            pass  # CSV 工具不可用时跳过

        # 知识库检索工具（第 3 周期）
        try:
            from .tools.kb_tools import search_knowledge_base
            self._tools.append(search_knowledge_base)
        except ImportError:
            pass  # 知识库工具不可用时跳过

        # 营销文案生成工具（第 4 周期）
        try:
            from .tools.copy_tools import generate_marketing_copy
            self._tools.append(generate_marketing_copy)
        except ImportError:
            pass  # 文案工具不可用时跳过

    def run(
        self,
        user_message: str,
        history_messages: Optional[List[dict]] = None,
    ) -> dict:
        """执行 Agent 对话。

        Args:
            user_message: 用户最新消息
            history_messages: 历史消息列表，格式 [{"role": "user/assistant", "content": "..."}]

        Returns:
            {"reply": "AI 回复内容", "tool_calls": [...]}
            tool_calls 在第 1 周期始终为空列表
        """
        # 构建消息列表
        messages: List[BaseMessage] = [SystemMessage(content=self._system_prompt)]

        # 加载历史消息（限制最近 20 条，避免超出 token 限制）
        if history_messages:
            for msg in history_messages[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))

        # 调用 LLM
        # 第 1 周期：直接调用 LLM（无工具）
        # 后续周期：通过 AgentExecutor + ReAct Agent 调用
        if self._tools:
            return self._run_with_tools(messages)
        else:
            return self._run_direct(messages)

    def _run_direct(self, messages: List[BaseMessage]) -> dict:
        """直接调用 LLM（无工具模式）。"""
        response = self.llm.invoke(messages)
        return {
            "reply": response.content,
            "tool_calls": [],
        }

    def _run_with_tools(self, messages: List[BaseMessage]) -> dict:
        """通过 bind_tools + 工具调用循环执行 Agent。

        不使用 hub.pull（依赖网络），而是利用 ChatOpenAI 原生
        tool calling 能力：LLM 自主决定是否调用工具，返回结果后继续推理。
        """
        # 绑定工具到 LLM（让模型知道有哪些工具可用）
        llm_with_tools = self.llm.bind_tools(self._tools)

        tool_calls_log = []
        max_turns = 5  # 防止无限循环

        for _ in range(max_turns):
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            # 检查是否有工具调用
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # 没有工具调用 → 最终回复
                return {
                    "reply": response.content or "抱歉，处理出错了。",
                    "tool_calls": tool_calls_log if tool_calls_log else None,
                }

            # 执行工具调用
            from langchain_core.messages import ToolMessage

            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")

                # 查找并执行工具
                tool_func = None
                for t in self._tools:
                    if t.name == tool_name:
                        tool_func = t
                        break

                if tool_func:
                    try:
                        result = tool_func.invoke(tool_args)
                    except Exception as e:
                        result = f"工具执行出错：{str(e)}"
                else:
                    result = f"未找到工具：{tool_name}"

                tool_calls_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": str(result)[:500],
                })

                messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

        # 超过最大轮次，返回最后一条 AI 消息
        last_ai = None
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                last_ai = m
                break

        return {
            "reply": last_ai.content if last_ai else "抱歉，分析过程超时，请简化问题重试。",
            "tool_calls": tool_calls_log if tool_calls_log else None,
        }


# ── 全局单例 ───────────────────────────────────────────────────
# 模块级 Agent 实例，整个应用共用

agent_service = AgentService()
