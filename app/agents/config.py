"""One AgentConfig per domain. Agents share all code (tools.py, chat.py) and differ only here:
instructions, and which tool set (app/agents/tools.py's TOOL_BUILDERS) is bound to the chat.

`instructions` below is a real, working default built from the classifier's own group descriptions
(app/classification/taxonomy.py) - generic on purpose. This is the file the team edits together to
write the actual system-prompt wording; nothing else in the agent scaffold needs to change for that.
"""
from dataclasses import dataclass

from app.classification.taxonomy import GROUPS

# Matches the ai_agents.agent_id / categories.agent_id seed rows in db/schema.sql.
GROUP_TO_AGENT_ID: dict[str, str] = {
    "Billing": "billing",
    "Metering": "metering",
    "Field services": "field_services",
    "Customer support": "customer_support",
    "General": "general",
}


@dataclass(frozen=True)
class AgentConfig:
    agent_id: str
    domain: str  # matches ai_agents.name / classification.group_name
    instructions: str  # system prompt


def _default_instructions(domain: str) -> str:
    return (
        f"You are an assistant for the {domain} team at Northwind Energy & Water, an electricity and "
        f"water utility, helping staff handle a case about {GROUPS[domain]['description']}. You never "
        "take any action yourself - you only look things up and explain, to make it easier for the "
        "member of staff you are talking to decide what to do. Use your tools when staff ask you to "
        "look something up or analyze the case, and only draft a reply to the customer when staff "
        "explicitly ask for one. Answer plainly and concisely."
    )


AGENT_CONFIGS: dict[str, AgentConfig] = {
    agent_id: AgentConfig(agent_id=agent_id, domain=domain, instructions=_default_instructions(domain))
    for domain, agent_id in GROUP_TO_AGENT_ID.items()
}
