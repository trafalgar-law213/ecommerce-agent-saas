"""
LangChain Agent 服务层。

封装 DeepSeek LLM 调用和 Agent 工具管理。
支持：
- 多轮工具调用（bind_tools + 手动循环）
- 调用追踪（耗时 / token / 工具使用）
- 流式输出（SSE 事件流）
"""

import time
import logging
from typing import Optional, List, Generator, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage,
)

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

# ── System Prompt ──────────────────────────────────────────────

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
        """注册 Agent 工具。

        Args:
            tools: LangChain @tool 装饰的函数列表
        """
        self._tools.extend(tools)

    def _auto_register_tools(self):
        """自动注册可用的 Agent 工具。"""
        # CSV 数据分析工具（第 2 周期）
        try:
            from .tools.csv_tools import analyze_sales_data
            self._tools.append(analyze_sales_data)
        except ImportError:
            pass

        # 知识库检索工具（第 3 周期）
        try:
            from .tools.kb_tools import search_knowledge_base
            self._tools.append(search_knowledge_base)
        except ImportError:
            pass

        # 营销文案生成工具（第 4 周期）
        try:
            from .tools.copy_tools import generate_marketing_copy
            self._tools.append(generate_marketing_copy)
        except ImportError:
            pass

    # ── 构建消息列表 ────────────────────────────────────────────

    def _build_messages(
        self,
        user_message: str,
        history_messages: Optional[List[dict]] = None,
    ) -> List[BaseMessage]:
        """构建发送给 LLM 的消息列表。"""
        messages: List[BaseMessage] = [SystemMessage(content=self._system_prompt)]

        if history_messages:
            for msg in history_messages[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))
        return messages

    # ── 工具执行 ────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """执行单个工具调用，返回结果字符串。"""
        tool_func = None
        for t in self._tools:
            if t.name == tool_name:
                tool_func = t
                break

        if not tool_func:
            return f"未找到工具：{tool_name}"

        try:
            result = tool_func.invoke(tool_args)
            return str(result)
        except Exception as e:
            logger.exception(f"工具 {tool_name} 执行失败")
            return f"工具执行出错：{str(e)}"

    # ── 提取 token 用量 ─────────────────────────────────────────

    def _extract_token_usage(self, response) -> Dict[str, int]:
        """从 LangChain 响应中提取 token 用量信息。"""
        usage = {"prompt": 0, "completion": 0, "total": 0}
        try:
            meta = getattr(response, "response_metadata", {}) or {}
            token_info = meta.get("token_usage", {})
            if token_info:
                usage["prompt"] = token_info.get("prompt_tokens", 0)
                usage["completion"] = token_info.get("completion_tokens", 0)
                usage["total"] = token_info.get("total_tokens", 0)
            # 备选：直接从 usage_metadata 读取
            usage_meta = getattr(response, "usage_metadata", None)
            if usage_meta:
                usage["prompt"] = usage_meta.get("input_tokens", 0) or usage["prompt"]
                usage["completion"] = usage_meta.get("output_tokens", 0) or usage["completion"]
                usage["total"] = usage_meta.get("total_tokens", 0) or usage["total"]
        except Exception:
            pass
        return usage

    # ── 同步调用（原有方法，增加指标追踪）──────────────────────

    def run(
        self,
        user_message: str,
        history_messages: Optional[List[dict]] = None,
    ) -> dict:
        """执行 Agent 对话（同步模式）。

        Returns:
            {"reply": "...", "tool_calls": [...], "trace": {...}}
        """
        start_time = time.perf_counter()
        messages = self._build_messages(user_message, history_messages)
        total_token_usage = {"prompt": 0, "completion": 0, "total": 0}

        if not self._tools:
            return self._run_direct(messages, start_time, total_token_usage)
        else:
            return self._run_with_tools(messages, start_time, total_token_usage)

    def _run_direct(
        self, messages: List[BaseMessage], start_time: float, token_usage: dict
    ) -> dict:
        """直接调用 LLM（无工具模式）。"""
        response = self.llm.invoke(messages)
        usage = self._extract_token_usage(response)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "reply": response.content,
            "tool_calls": None,
            "trace": {
                "duration_ms": duration_ms,
                "tool_count": 0,
                "tools_called": None,
                "turn_count": 1,
                "token_usage": usage,
                "status": "success",
            },
        }

    def _run_with_tools(
        self, messages: List[BaseMessage], start_time: float, token_usage: dict
    ) -> dict:
        """通过 bind_tools + 工具调用循环执行 Agent。"""
        llm_with_tools = self.llm.bind_tools(self._tools)

        tool_calls_log = []
        max_turns = 5
        total_turns = 0

        for turn in range(max_turns):
            total_turns = turn + 1
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            # 累计 token 用量
            turn_usage = self._extract_token_usage(response)
            for k in token_usage:
                token_usage[k] += turn_usage.get(k, 0)

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return {
                    "reply": response.content or "抱歉，处理出错了。",
                    "tool_calls": tool_calls_log if tool_calls_log else None,
                    "trace": {
                        "duration_ms": duration_ms,
                        "tool_count": len(tool_calls_log),
                        "tools_called": [tc["tool"] for tc in tool_calls_log] if tool_calls_log else None,
                        "turn_count": total_turns,
                        "token_usage": token_usage,
                        "status": "success",
                    },
                }

            # 执行工具调用
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")

                result = self._execute_tool(tool_name, tool_args)

                tool_calls_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": str(result)[:500],
                })

                messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

        # 超过最大轮次
        last_ai = None
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                last_ai = m
                break

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "reply": last_ai.content if last_ai else "抱歉，分析过程超时，请简化问题重试。",
            "tool_calls": tool_calls_log if tool_calls_log else None,
            "trace": {
                "duration_ms": duration_ms,
                "tool_count": len(tool_calls_log),
                "tools_called": [tc["tool"] for tc in tool_calls_log] if tool_calls_log else None,
                "turn_count": total_turns,
                "token_usage": token_usage,
                "status": "max_turns_exceeded" if not last_ai or not last_ai.content else "success",
            },
        }

    # ── 流式调用（新增）─────────────────────────────────────────

    def run_stream(
        self,
        user_message: str,
        history_messages: Optional[List[dict]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """执行 Agent 对话（流式模式），逐事件 yield。

        事件类型：
        - {"type": "tool_start", "tool": "...", "args": {...}}
        - {"type": "tool_end",   "tool": "...", "result_preview": "..."}
        - {"type": "text",       "content": "..."}
        - {"type": "done",       "duration_ms": N, "tool_calls": [...], "token_usage": {...}}
        - {"type": "error",      "message": "..."}

        Yields:
            Dict[str, Any]: SSE 事件数据
        """
        start_time = time.perf_counter()
        total_token_usage = {"prompt": 0, "completion": 0, "total": 0}

        try:
            messages = self._build_messages(user_message, history_messages)

            if not self._tools:
                # 无工具：直接获取回复并 yield
                response = self.llm.invoke(messages)
                usage = self._extract_token_usage(response)
                for k in total_token_usage:
                    total_token_usage[k] += usage.get(k, 0)
                if response.content:
                    yield {"type": "text", "content": response.content}
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                yield {
                    "type": "done",
                    "duration_ms": duration_ms,
                    "tool_calls": None,
                    "token_usage": total_token_usage,
                }
                return

            # 有工具：逐轮 invoke
            llm_with_tools = self.llm.bind_tools(self._tools)
            tool_calls_log = []
            max_turns = 5
            total_turns = 0

            for turn in range(max_turns):
                total_turns = turn + 1
                response = llm_with_tools.invoke(messages)
                messages.append(response)

                # 累计 token
                turn_usage = self._extract_token_usage(response)
                for k in total_token_usage:
                    total_token_usage[k] += turn_usage.get(k, 0)

                tool_calls = getattr(response, "tool_calls", None) or []

                if not tool_calls:
                    # 最终回复
                    if response.content:
                        yield {"type": "text", "content": response.content}
                    break

                # 执行工具
                for tc in tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", "")

                    yield {"type": "tool_start", "tool": tool_name, "args": tool_args}

                    result = self._execute_tool(tool_name, tool_args)

                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "result_preview": str(result)[:200],
                    }

                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": str(result)[:500],
                    })

                    messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_id)
                    )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            yield {
                "type": "done",
                "duration_ms": duration_ms,
                "tool_calls": tool_calls_log if tool_calls_log else None,
                "token_usage": total_token_usage,
            }

        except Exception as e:
            logger.exception("Agent 流式调用失败")
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            yield {"type": "error", "message": str(e)}
            yield {
                "type": "done",
                "duration_ms": duration_ms,
                "tool_calls": None,
                "token_usage": total_token_usage,
            }


# ── 全局单例 ───────────────────────────────────────────────────

agent_service = AgentService()
