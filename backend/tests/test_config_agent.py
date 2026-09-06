from app.config import settings


def test_agent_settings_defaults():
    assert settings.gemini_model
    assert settings.gemini_fallback_model
    assert settings.agent_max_tool_iterations >= 4
    assert settings.agent_max_rows >= 10
    assert settings.checkpoint_collection == "chat_checkpoints"
