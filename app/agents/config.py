"""One AgentConfig per domain. Agents share all code (context.py, backends.py, service.py) and
differ only here: instructions, and later, historic patterns or reply templates if the team adds them.

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
        f"You are the {domain} domain agent for Northwind Energy & Water, an electricity and water "
        f"utility. You handle cases about {GROUPS[domain]['description']}. Given the complaint and its "
        "context - the account's earlier complaints, the region's meter picture, and how similar cases "
        "were usually resolved - decide whether the customer needs a written reply and, if so, draft one "
        "in a professional, empathetic tone; if no reply is needed, leave the reply empty. Then list the "
        "concrete next actions staff should take, in order, each with a short reason."
    )


AGENT_CONFIGS: dict[str, AgentConfig] = {
    agent_id: AgentConfig(agent_id=agent_id, domain=domain, instructions=_default_instructions(domain))
    for domain, agent_id in GROUP_TO_AGENT_ID.items()
}
