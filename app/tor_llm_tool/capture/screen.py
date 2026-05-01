from __future__ import annotations

from PIL import Image

from tor_llm_tool.errors import AppError, ErrorCategory


def capture_region(x: int, y: int, width: int, height: int) -> Image.Image:
    if width <= 2 or height <= 2:
        raise AppError(
            code="EMPTY_REGION",
            category=ErrorCategory.VALIDATION,
            message="選択範囲が小さすぎます。",
            retryable=True,
            user_action="もう少し大きい範囲を選択してください。",
        )

    try:
        import mss
    except ImportError as exc:
        raise AppError(
            code="CAPTURE_FAILED",
            category=ErrorCategory.CAPTURE,
            message="スクリーンショット機能を読み込めませんでした。",
            detail="mss がインストールされていません。",
            retryable=False,
        ) from exc

    try:
        with mss.mss() as sct:
            raw = sct.grab({"left": x, "top": y, "width": width, "height": height})
            return Image.frombytes("RGB", raw.size, raw.rgb)
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="CAPTURE_FAILED",
            category=ErrorCategory.CAPTURE,
            message="スクリーンショットを取得できませんでした。",
            detail=str(exc),
            retryable=True,
        ) from exc

