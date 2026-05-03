from __future__ import annotations

from tor_llm_tool.models import AssistantRequest
from tor_llm_tool.settings.config import PromptConfig


def build_user_prompt(request: AssistantRequest, prompts: PromptConfig | None = None) -> str:
    parts = [
        f"タスク: {request.task}",
        f"説明の深さ: {request.explanation_level}",
        f"翻訳先言語: {request.target_language}",
    ]

    if request.send_context:
        context_lines = []
        if request.context.app_name:
            context_lines.append(f"アプリ名: {request.context.app_name}")
        if request.context.process_name:
            context_lines.append(f"プロセス名: {request.context.process_name}")
        if request.context.window_title:
            context_lines.append(f"ウィンドウタイトル: {request.context.window_title}")
        if request.context.url:
            context_lines.append(f"URL: {request.context.url}")
        if request.context.url_candidates:
            context_lines.append("URL候補: " + ", ".join(request.context.url_candidates))
        if context_lines:
            parts.append("コンテキスト:\n" + "\n".join(context_lines))

    if request.send_ocr_text and request.ocr_text.strip():
        parts.append("OCRテキスト:\n" + request.ocr_text.strip())
    elif request.send_ocr_text:
        parts.append("OCRテキスト: なし")

    if request.question.strip():
        parts.append("ユーザーの質問:\n" + request.question.strip())

    if request.previous_turns:
        lines = []
        for index, turn in enumerate(request.previous_turns[-6:], start=1):
            lines.append(
                f"{index}. task={turn.task}\n"
                f"Q: {turn.question.strip() or '(質問なし)'}\n"
                f"A: {turn.answer.strip()}"
            )
        parts.append("同じ選択範囲での直近の会話履歴:\n" + "\n\n".join(lines))

    parts.append(_task_instruction(request, prompts))
    return "\n\n".join(parts)


def _task_instruction(request: AssistantRequest, prompts: PromptConfig | None) -> str:
    if prompts is None:
        prompts = PromptConfig()
    return prompts.instruction_for(request.task)
