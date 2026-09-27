from agents import OpenAIChatCompletionsModel

from agent import build_copilot


def test_gemini_uses_chat_completions_adapter_without_network(monkeypatch):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    copilot = build_copilot()
    assert isinstance(copilot.model, OpenAIChatCompletionsModel)
    assert copilot.model.model == "gemini-3.1-flash-lite"
