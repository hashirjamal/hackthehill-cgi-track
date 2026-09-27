"""Runs the domain agent once, for one of the two buttons on a complaint's case view.

There is no conversation and nothing is returned here - a tool's own side effect (an ActionItem
or a DraftResponse row, see app/agents/tools.py) is the actual output. The caller reads that back
from the database after invoking. AgentBackendError is the only exception this can raise from a
model/tool-loop failure; anything else is a bug in this code, not a backend failure, and should
propagate.
"""
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.agents.config import AgentConfig

DEFAULT_SYSTEM_PROMPT = "You are a support agent assistant. Help staff understand and resolve this case."

GET_CONTEXT_INSTRUCTION = (
    "Use your tools to understand this case, then call create_action_brief once per concrete "
    "next action staff should take, in the order they should tackle them. Do not draft anything "
    "for the customer."
)

GENERATE_DRAFT_INSTRUCTION = (
    "Staff have asked for a drafted reply to the customer for this case. Use your tools to "
    "gather whatever context is relevant, then call save_draft_reply exactly once with your "
    "best draft, in a professional and empathetic tone."
)


class AgentBackendError(Exception):
    """The model/tool loop failed. Callers must not let this raise past them - the case stays in
    the queue with no new action items/draft, nothing else blocks (requirement B5)."""


def run_agent_once(model: BaseChatModel, cfg: AgentConfig | None, tools: list, instruction: str) -> None:
    try:
        agent = create_agent(model=model, tools=tools, system_prompt=cfg.instructions if cfg else DEFAULT_SYSTEM_PROMPT)
        agent.invoke({"messages": [HumanMessage(content=instruction)]})
    except Exception as e:
        raise AgentBackendError(f"Agent run failed: {e}") from e
