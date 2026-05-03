from tor_llm_tool.assistant.prompts import build_user_prompt
from tor_llm_tool.models import AssistantRequest, CaptureContext, ConversationTurn
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


def test_build_user_prompt_includes_previous_turns():
    request = AssistantRequest(
        task="ask-region",
        ocr_text="current",
        context=CaptureContext(),
        question="follow up?",
        previous_turns=[
            ConversationTurn(question="first?", answer="first answer", task="ask-region")
        ],
    )

    prompt = build_user_prompt(request)

    assert "同じ選択範囲での直近の会話履歴" in prompt
    assert "first answer" in prompt
