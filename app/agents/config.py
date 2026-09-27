"""One AgentConfig per domain. Agents share all code (tools.py, runner.py) and differ only here:
instructions, and (for general) an extra tool - see app/agents/tools.py's build_context_tools_for.

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
        "take any real action yourself - you only look things up, using your tools, to make it easier "
        "for staff to decide what to do next. Follow the task you are given exactly: it will ask you "
        "either for action items or for a drafted reply, never both. Be plain and concise."
    )


AGENT_CONFIGS: dict[str, AgentConfig] = {
    agent_id: AgentConfig(agent_id=agent_id, domain=domain, instructions=_default_instructions(domain))
    for domain, agent_id in GROUP_TO_AGENT_ID.items()
}
