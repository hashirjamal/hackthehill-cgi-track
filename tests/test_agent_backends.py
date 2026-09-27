import json

import pytest

from app.agents.backends import AgentBackendError, OllamaBackend, TemplateBackend
from app.agents.config import AGENT_CONFIGS
from app.agents.schemas import AgentContext, AgentDraftOutput, CaseProfile
from app.classification.schemas import ComplaintIn


class _Message:
    def __init__(self, content: str):
        self.content = content


class _Response:
    def __init__(self, content: str):
        self.message = _Message(content)


class FakeOllamaClient:
    """Returns a canned chat response, or raises what's given, in place of a real Ollama server."""

    def __init__(self, content: str | None = None, raise_: Exception | None = None):
        self._content = content
        self._raise = raise_
        self.calls = []

    def chat(self, model, messages, format):
        self.calls.append({"model": model, "messages": messages, "format": format})
        if self._raise:
            raise self._raise
        return _Response(self._content)


def test_template_backend_recommends_review_with_no_history():
    backend = TemplateBackend()
    out = backend.draft(AGENT_CONFIGS["billing"], ComplaintIn(text="x"), AgentContext())
    assert out.draft_reply is None
    assert len(out.action_items) == 1
    assert "No case history" in out.action_items[0].rationale


def test_template_backend_drafts_a_reply_for_mostly_information_only_categories():
    ctx = AgentContext(case_profile=CaseProfile(
        category="Service - poor communication", region="Ashford", source_system="SYS-02",
        n=100, avg_days=10.0, info_only_share=0.6, transfer_rate=0.1, reopen_rate=0.05,
        breach_rate=0.2, top_resolution="Information provided",
    ))
    out = TemplateBackend().draft(AGENT_CONFIGS["customer_support"], ComplaintIn(text="x"), ctx)
    assert out.draft_reply is not None


def test_ollama_backend_sends_the_configured_model_and_a_json_schema_format():
    valid = json.dumps({"draft_reply": None, "action_items": []})
    client = FakeOllamaClient(content=valid)
    backend = OllamaBackend(model="gemma3", host="http://localhost:11434", client=client)
    out = backend.draft(AGENT_CONFIGS["billing"], ComplaintIn(text="x"), AgentContext())
    assert isinstance(out, AgentDraftOutput)
    assert client.calls[0]["model"] == "gemma3"
    assert client.calls[0]["format"] == AgentDraftOutput.model_json_schema()
    assert client.calls[0]["messages"][0]["role"] == "system"


def test_ollama_backend_parses_a_full_response():
    payload = {
        "draft_reply": "We're sorry for the delay.",
        "action_items": [{"action_type": "correct_bill", "description": "Reissue the bill",
                           "rationale": "Estimated read", "rank": 1}],
    }
    client = FakeOllamaClient(content=json.dumps(payload))
    backend = OllamaBackend(model="gemma3", host="http://localhost:11434", client=client)
    out = backend.draft(AGENT_CONFIGS["billing"], ComplaintIn(text="x"), AgentContext())
    assert out.draft_reply == "We're sorry for the delay."
    assert out.action_items[0].action_type == "correct_bill"


def test_ollama_backend_wraps_a_connection_failure():
    client = FakeOllamaClient(raise_=ConnectionRefusedError("connection refused"))
    backend = OllamaBackend(model="gemma3", host="http://localhost:11434", client=client)
    with pytest.raises(AgentBackendError):
        backend.draft(AGENT_CONFIGS["billing"], ComplaintIn(text="x"), AgentContext())


def test_ollama_backend_wraps_malformed_json():
    client = FakeOllamaClient(content="not json at all")
    backend = OllamaBackend(model="gemma3", host="http://localhost:11434", client=client)
    with pytest.raises(AgentBackendError):
        backend.draft(AGENT_CONFIGS["billing"], ComplaintIn(text="x"), AgentContext())


def test_ollama_backend_wraps_json_that_does_not_match_the_schema():
    client = FakeOllamaClient(content=json.dumps({"draft_reply": 123}))  # wrong type, missing action_items
    backend = OllamaBackend(model="gemma3", host="http://localhost:11434", client=client)
    with pytest.raises(AgentBackendError):
        backend.draft(AGENT_CONFIGS["billing"], ComplaintIn(text="x"), AgentContext())
