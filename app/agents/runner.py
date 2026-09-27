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
    "Use your tools to check this customer's records in Northwind's systems, then call "
    "create_action_brief once per concrete next action staff should take (usually 2 to 5), most "
    "urgent first. Base every action on something you found, and in its rationale name the system "
    "and the fact, for example \"Aurora: last 3 bills estimated, latest £412 vs usual £180\". "
    "Flag vulnerability (Priority Services Register) and repeat contacts first. If the customer "
    "already gave us something - a meter reading, a photo, an explanation - use it rather than "
    "booking a visit or asking again. Do not draft anything for the customer."
)

GENERATE_DRAFT_INSTRUCTION = (
    "Staff have asked for a drafted reply to the customer for this case. Use your tools to check "
    "the customer's records, then call save_draft_reply exactly once. Address the customer by "
    "name, refer to the specific facts you found (amounts, dates, what they told us), and never "
    "ask for anything we already hold, such as their account number or a reading they already "
    "submitted. Do not promise refunds, credits or dates that the records do not confirm - say "
    "what staff will check instead. Warm, plain, professional; under 200 words; sign off as "
    "\"[Your name], Northwind Energy & Water\"."
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
