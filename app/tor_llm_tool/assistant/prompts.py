from __future__ import annotations

from tor_llm_tool.models import AssistantRequest


SYSTEM_PROMPT = """あなたは画面範囲の読解支援ツールです。
入力にはスクリーンショット画像、OCRテキスト、アプリ名、ウィンドウタイトル、URL候補が含まれる場合があります。
OCRには誤りがあり得ます。画像・OCR・コンテキストのどれを根拠にしたかを区別し、判断できないことは断定しないでください。
回答は日本語で、簡潔かつ実用的に書いてください。"""


def build_user_prompt(request: AssistantRequest) -> str:
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

    parts.append(_task_instruction(request))
    return "\n\n".join(parts)


def _task_instruction(request: AssistantRequest) -> str:
    if request.task == "translate-region":
        return (
            "指示: OCRテキストと画像を参考に、内容を自然な日本語へ翻訳してください。"
            "出力は「翻訳」「OCR上の不確実点」「補足」に分けてください。"
        )
    if request.task == "ask-region":
        return (
            "指示: ユーザーの質問に、選択範囲の画像・OCRテキスト・コンテキストを根拠に回答してください。"
            "範囲内情報だけで答えられない場合は、その旨を明確にしてください。"
        )
    if request.task == "clean-ocr":
        return (
            "指示: OCRテキストを読みやすく整形してください。"
            "誤認識の推測修正は最小限にし、表・箇条書き・コード・ログの構造を保ってください。"
        )
    if request.task == "extract-structured":
        return "指示: 選択範囲の情報を構造化して、見出し・項目・値・注意点に分けてください。"
    return (
        "指示: 選択範囲の内容を説明してください。"
        "短い要約、文脈、重要点、不明点を分け、画像/OCR/推測を区別してください。"
    )

