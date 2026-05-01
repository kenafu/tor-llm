from __future__ import annotations

from PIL import Image

from tor_llm_tool.errors import AppError, ErrorCategory
from tor_llm_tool.models import OcrResult
from tor_llm_tool.ocr.base import OcrEngine


class TesseractOcrEngine(OcrEngine):
    def __init__(self, languages: list[str]) -> None:
        self.languages = languages

    def recognize(self, image: Image.Image) -> OcrResult:
        try:
            import pytesseract
        except ImportError as exc:
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail="pytesseract がインストールされていません。",
                retryable=True,
            ) from exc

        lang_map = {"ja": "jpn", "en": "eng"}
        lang = "+".join(lang_map.get(item, item) for item in self.languages)
        try:
            text = pytesseract.image_to_string(image, lang=lang)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail=str(exc),
                retryable=True,
            ) from exc
        return OcrResult(text=text.strip())

