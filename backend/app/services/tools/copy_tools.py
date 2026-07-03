"""
营销文案生成工具 — 供 LangChain Agent 调用。

Agent 可以调用 generate_marketing_copy 工具为商品生成不同风格和渠道的推广文案。
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ...config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# 工具内部独立 LLM 实例（用于文案生成，temperature 略高以增加创意）
_copy_llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.85,
    max_tokens=1024,
)

# ── 文案风格与渠道的提示词模板 ──────────────────────────────

STYLE_PROMPTS = {
    "活泼": "使用轻松活泼的语气，多用emoji和网络流行语，让文案读起来有趣、有感染力，适合年轻消费群体。",
    "专业": "使用专业、严谨的语气，突出产品的技术参数、品质保证和权威背书，适合高端消费群体。",
    "简洁": "使用简洁有力的短句，信息密度高，一针见血，适合快节奏浏览场景。",
}

CHANNEL_FORMATS = {
    "小红书": (
        "小红书风格：标题要抓眼球，正文分点种草，使用「✨🔥💯」等 emoji，"
        "末尾加上相关话题标签（如 #好物推荐 #必入清单）。"
        "语气像朋友分享好物，真实感强，不要太像广告。"
    ),
    "朋友圈": (
        "朋友圈风格：短小精悍，3-5 句话即可，语气像日常分享，"
        "可以适当加入个人感受和使用体验。不要过度营销，保持亲切自然。"
    ),
    "详情页": (
        "商品详情页风格：结构清晰，包含「产品亮点」「核心卖点」「规格参数」"
        "「适用场景」「售后保障」等板块。语言精炼专业，突出差异化优势，"
        "用 bullet points 组织信息，便于用户快速浏览决策。"
    ),
}


@tool
def generate_marketing_copy(
    product_info: str,
    style: str = "活泼",
    channel: str = "小红书",
) -> str:
    """为指定商品生成营销推广文案。

    当用户提出以下需求时，必须调用此工具：
    - "帮我写一篇文案"、"生成推广文案"、"写营销文案"
    - "帮我写小红书/朋友圈/详情页文案"
    - "给这个商品写一段种草文案"
    - "帮我润色这段产品介绍"
    - 任何需要生成或优化商品推广文字的场景

    Args:
        product_info: 商品信息，包括商品名称、卖点、价格、目标用户等，越详细越好
        style: 文案风格，可选「活泼」「专业」「简洁」，默认「活泼」
        channel: 发布渠道，可选「小红书」「朋友圈」「详情页」，默认「小红书」

    Returns:
        生成的营销文案文本。
    """

    # 参数校验与默认值
    if style not in STYLE_PROMPTS:
        style = "活泼"
    if channel not in CHANNEL_FORMATS:
        channel = "小红书"

    style_guide = STYLE_PROMPTS[style]
    channel_guide = CHANNEL_FORMATS[channel]

    # ── 构建生成提示词 ──────────────────────────────────────
    prompt = f"""你是一位资深的电商营销文案专家。请根据以下商品信息，撰写一篇高质量的营销推广文案。

【商品信息】
{product_info.strip()}

【风格要求】
{style_guide}

【渠道格式】
{channel_guide}

【硬性要求】
- 不要编造商品信息中没有的卖点或参数
- 文案长度适中，{channel}渠道适配
- 用中文撰写
- 直接输出文案正文，不需要说明"以下是为您生成的文案"之类的引导语"""

    # ── 调用 LLM 生成 ──────────────────────────────────────
    try:
        response = _copy_llm.invoke(prompt)
        copy_text = response.content.strip()
        return f"📝 已为您生成 {channel} · {style}风格 营销文案：\n\n{copy_text}"
    except Exception as e:
        return f"❌ 文案生成失败：{str(e)}。请稍后重试或检查商品信息是否合理。"
