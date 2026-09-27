"""Tests run_agent_once using a scripted fake chat model - the same dependency-injection style
as FakeLaya (tests/test_service.py) - so no real Ollama server or LangChain agent internals need
to run for real."""
import pytest
from langchain.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agents.config import AGENT_CONFIGS
from app.agents.runner import AgentBackendError, run_agent_once


class ScriptedChatModel(FakeMessagesListChatModel):
    """FakeMessagesListChatModel with bind_tools made a no-op (it's fake regardless of the
    tool schema), since create_agent calls bind_tools() before every model invocation."""

    def bind_tools(self, tools, **kwargs):
        return self


class RaisingChatModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, *args, **kwargs):
        raise RuntimeError("Ollama is not running")


def test_calls_the_tool_the_model_asks_for():
    calls = []

    @tool
    def create_action_brief(action_type: str, description: str, rationale: str) -> str:
        """Record an action item."""
        calls.append((action_type, description, rationale))
        return "recorded"

    model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "create_action_brief",
            "args": {"action_type": "correct_bill", "description": "Reissue the bill", "rationale": "Estimated read"},
            "id": "1",
        }]),
        AIMessage(content="Done."),
    ])
    run_agent_once(model, AGENT_CONFIGS["billing"], [create_action_brief], "Analyze this case.")
    assert calls == [("correct_bill", "Reissue the bill", "Estimated read")]


def test_works_with_no_tools_and_no_config():
    model = ScriptedChatModel(responses=[AIMessage(content="Acknowledged.")])
    run_agent_once(model, None, [], "Do something.")  # just confirms it doesn't raise


def test_wraps_a_model_failure_as_agent_backend_error():
    model = RaisingChatModel(responses=[])
    with pytest.raises(AgentBackendError):
        run_agent_once(model, AGENT_CONFIGS["billing"], [], "Analyze this case.")
