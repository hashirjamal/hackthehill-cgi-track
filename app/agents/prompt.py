"""Renders a complaint and its AgentContext into the user-turn text given to the backend."""
from app.agents.schemas import AgentContext
from app.classification.schemas import ComplaintIn


def _pct(value: float | None) -> str:
    return f"{value * 100:.0f}%" if value is not None else "unknown"


def render_agent_prompt(complaint: ComplaintIn, context: AgentContext) -> str:
    parts = ["Complaint:"]
    if complaint.category:
        parts.append(f"- Category: {complaint.category}")
    if complaint.region:
        parts.append(f"- Region: {complaint.region}")
    if complaint.channel:
        parts.append(f"- Channel: {complaint.channel}")
    if complaint.priority:
        parts.append(f"- Priority: {complaint.priority}")
    if complaint.text:
        parts.append(f"- Customer said: {complaint.text}")

    profile = context.case_profile
    parts.append("\nHow similar cases were usually handled:")
    if profile:
        parts.append(
            f"- Of {profile.n} similar closed cases: average {profile.avg_days} days to close, "
            f"{_pct(profile.info_only_share)} needed only information, {_pct(profile.transfer_rate)} were "
            f"transferred, {_pct(profile.reopen_rate)} were reopened, {_pct(profile.breach_rate)} breached "
            f"the SLA. Most common resolution: {profile.top_resolution or 'no single common resolution'}."
        )
    else:
        parts.append("- No matching case history for this category, region and system.")

    parts.append("\nThis account's earlier complaints (most recent first):")
    if context.account_history:
        for h in context.account_history:
            resolution = f"resolved as {h.resolution_action}" if h.resolution_action else "no resolution recorded"
            repeat = " [repeat contact]" if h.is_repeat else ""
            parts.append(f"- {h.date_opened}: {h.category} ({h.status}), {resolution}{repeat}")
    else:
        parts.append("- No earlier complaints on this account.")

    meter = context.region_meter_picture
    parts.append("\nThis region's meter picture:")
    if meter:
        parts.append(
            f"- {meter.month}: {_pct(meter.estimated_read_rate)} of bills are estimated reads, "
            f"{_pct(meter.smart_meter_penetration)} smart-meter penetration, "
            f"{meter.billing_exceptions_per_1000 if meter.billing_exceptions_per_1000 is not None else '?'} "
            "billing exceptions per 1,000 accounts."
        )
    else:
        parts.append("- No meter data for this region and month.")

    return "\n".join(parts)
