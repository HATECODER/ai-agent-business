from agents import OpenAIChatCompletionsModel

from agent import build_copilot


def test_gemini_uses_chat_completions_adapter_without_network(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    copilot = build_copilot(seeded_db)
    assert isinstance(copilot.model, OpenAIChatCompletionsModel)
    assert copilot.model.model == "gemini-3.1-flash-lite"
    assert copilot.model_settings.store is None


def test_openai_disables_provider_storage(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-sent")
    copilot = build_copilot(seeded_db)
    assert copilot.model_settings.store is False
