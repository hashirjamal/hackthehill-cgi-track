"""Tests run_chat_turn's tool loop and draft-detection using a scripted fake chat model -
the same dependency-injection style as FakeLaya (tests/test_service.py) - so no real Ollama
server or LangChain agent internals need to run for real."""
from langchain.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agents.chat import run_chat_turn
from app.agents.config import AGENT_CONFIGS


class ScriptedChatModel(FakeMessagesListChatModel):
    """FakeMessagesListChatModel with bind_tools made a no-op (it's fake regardless of the
    tool schema), since create_agent calls bind_tools() before every model invocation."""

    def bind_tools(self, tools, **kwargs):
        return self


@tool
def get_case_profile() -> str:
    """Look up the historic pattern for this case."""
    return "Similar cases usually take 12 days and are resolved as a bill correction."


@tool
def save_draft_reply(body: str) -> str:
    """Save a drafted reply to the customer."""
    return "Draft saved for staff review."


def test_returns_the_final_reply_with_no_draft_when_no_draft_tool_was_called():
    model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_case_profile", "args": {}, "id": "1"}]),
        AIMessage(content="Similar cases usually get a bill correction within about 12 days."),
    ])
    reply, draft_saved = run_chat_turn(model, AGENT_CONFIGS["billing"], [get_case_profile], [], "How do similar cases usually go?")
    assert reply == "Similar cases usually get a bill correction within about 12 days."
    assert draft_saved is False


def test_detects_when_save_draft_reply_was_called():
    model = ScriptedChatModel(responses=[
        AIMessage(
            content="",
            tool_calls=[{"name": "save_draft_reply", "args": {"body": "Sorry for the delay."}, "id": "1"}],
        ),
        AIMessage(content="I've saved a draft for you to review."),
    ])
    reply, draft_saved = run_chat_turn(
        model, AGENT_CONFIGS["billing"], [save_draft_reply], [], "Draft a reply apologizing for the delay."
    )
    assert reply == "I've saved a draft for you to review."
    assert draft_saved is True


def test_works_with_no_tools_at_all():
    model = ScriptedChatModel(responses=[AIMessage(content="This is a general information question.")])
    reply, draft_saved = run_chat_turn(model, None, [], [], "What does an estimated bill mean?")
    assert reply == "This is a general information question."
    assert draft_saved is False


def test_prior_history_is_included_before_the_new_message():
    model = ScriptedChatModel(responses=[AIMessage(content="Following up on that: yes, it's a repeat contact.")])
    history = [("staff", "Is this account's first complaint?"), ("assistant", "No, they've complained twice before.")]
    reply, _ = run_chat_turn(model, AGENT_CONFIGS["billing"], [], history, "Is that a repeat contact flag?")
    assert reply == "Following up on that: yes, it's a repeat contact."
