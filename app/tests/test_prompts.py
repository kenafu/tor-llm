from tor_llm_tool.assistant.prompts import build_user_prompt
from tor_llm_tool.models import AssistantRequest, CaptureContext
from tor_llm_tool.settings.config import PromptConfig


def test_build_user_prompt_uses_custom_template():
    request = AssistantRequest(
        task="explain-region",
        ocr_text="hello",
        context=CaptureContext(app_name="DemoApp"),
    )
    prompts = PromptConfig(explain_region="CUSTOM EXPLAIN")

    prompt = build_user_prompt(request, prompts)

    assert "CUSTOM EXPLAIN" in prompt
    assert "DemoApp" in prompt


def test_prompt_config_accepts_task_aliases():
    prompts = PromptConfig.model_validate({"translate-region": "CUSTOM TRANSLATE"})

    assert prompts.instruction_for("translate-region") == "CUSTOM TRANSLATE"
