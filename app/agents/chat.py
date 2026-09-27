"""Runs one turn of a staff <-> domain-agent chat about a single complaint.

The model is given tools scoped to that complaint (app/agents/tools.py) and decides for itself
whether to call any before answering. Nothing here executes a real action on any account - the
only tool with a side effect (save_draft_reply) writes a DraftResponse row for staff to review.
"""
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.config import AgentConfig

NO_LLM_REPLY = (
    "AI assistance is turned off right now. Please review the case data and account history "
    "in the dashboard directly."
)

DEFAULT_SYSTEM_PROMPT = "You are a support agent assistant. Help staff understand and resolve this case."


def run_chat_turn(
    model: BaseChatModel,
    cfg: AgentConfig | None,
    tools: list,
    history: list[tuple[str, str]],
    message: str,
) -> tuple[str, bool]:
    """Returns (reply text, whether save_draft_reply was called this turn). `history` is
    (role, content) pairs, role either "staff" or "assistant"."""
    agent = create_agent(model=model, tools=tools, system_prompt=cfg.instructions if cfg else DEFAULT_SYSTEM_PROMPT)

    messages = [
        HumanMessage(content=content) if role == "staff" else AIMessage(content=content)
        for role, content in history
    ]
    messages.append(HumanMessage(content=message))

    result = agent.invoke({"messages": messages})
    result_messages = result["messages"]

    draft_saved = any(
        isinstance(m, AIMessage) and any(tc["name"] == "save_draft_reply" for tc in (m.tool_calls or []))
        for m in result_messages
    )
    reply = next((m.content for m in reversed(result_messages) if isinstance(m, AIMessage) and m.content), "")
    return reply, draft_saved
