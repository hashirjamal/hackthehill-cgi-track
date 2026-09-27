"""Two interchangeable backends for turning a case + context into a draft reply and action items.

OllamaBackend calls a local Ollama model with JSON-schema-constrained structured output in a single
call - no multi-turn tool-calling loop, since the model the team ends up running (gemma3 is a
placeholder tag; see app/config.py) cannot be assumed to support reliable function calling. All the
context an agent needs is assembled server-side (app/agents/context.py) before the call.

TemplateBackend is the N6 confidentiality fallback (docs/requirements.md): no LLM call at all, a
deterministic template filled from case data. It doubles as the offline-testable default.
"""
from typing import Any, Protocol

import ollama

from app.agents.config import AgentConfig
from app.agents.prompt import render_agent_prompt
from app.agents.schemas import ActionItemOut, AgentContext, AgentDraftOutput
from app.classification.schemas import ComplaintIn


class AgentBackendError(Exception):
    """The backend could not produce a draft. Callers must not let this stop the batch (requirement B5)."""


class AgentBackend(Protocol):
    model_name: str

    def draft(self, cfg: AgentConfig, complaint: ComplaintIn, context: AgentContext) -> AgentDraftOutput: ...


class TemplateBackend:
    """No LLM: fills a deterministic template from case data (N6 confidentiality fallback)."""

    model_name = "template"

    def draft(self, cfg: AgentConfig, complaint: ComplaintIn, context: AgentContext) -> AgentDraftOutput:
        profile = context.case_profile
        if profile is None:
            rationale = "No case history is available for this category, region and system."
        else:
            rationale = (
                f"Similar cases usually take {profile.avg_days} days and are usually resolved as: "
                f"{profile.top_resolution or 'no single common resolution'}."
            )
        action_items = [
            ActionItemOut(
                action_type="review_case",
                description=f"Review this {cfg.domain} case and confirm the next step with the customer.",
                rationale=rationale,
                rank=1,
            )
        ]
        draft_reply = None
        if profile and profile.info_only_share is not None and profile.info_only_share >= 0.5:
            draft_reply = (
                f"Thank you for contacting us about your {complaint.category or cfg.domain.lower()} query. "
                "We are reviewing your case and will confirm the outcome shortly."
            )
        return AgentDraftOutput(draft_reply=draft_reply, action_items=action_items)


class OllamaBackend:
    """Calls a local Ollama model. `client` is injectable for tests (see tests/test_agent_backends.py)."""

    def __init__(self, model: str, host: str, client: Any | None = None, timeout: float = 30.0):
        self.model_name = model
        # ollama.Client's own timeout defaults to None (wait forever), which would let a hung server
        # hold the request and its database transaction open indefinitely. A timeout surfaces as an
        # exception from chat(), so it becomes an AgentBackendError like any other call failure.
        self._client = client if client is not None else ollama.Client(host=host, timeout=timeout)

    def draft(self, cfg: AgentConfig, complaint: ComplaintIn, context: AgentContext) -> AgentDraftOutput:
        messages = [
            {"role": "system", "content": cfg.instructions},
            {"role": "user", "content": render_agent_prompt(complaint, context)},
        ]
        try:
            response = self._client.chat(
                model=self.model_name, messages=messages, format=AgentDraftOutput.model_json_schema()
            )
        except Exception as e:
            raise AgentBackendError(f"Ollama call failed: {e}") from e

        try:
            return AgentDraftOutput.model_validate_json(response.message.content)
        except ValueError as e:
            # pydantic.ValidationError (invalid JSON or a schema mismatch) subclasses ValueError.
            raise AgentBackendError(f"Ollama returned output that did not match the schema: {e}") from e
