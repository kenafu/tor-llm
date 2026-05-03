from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from tor_llm_tool.errors import AppError, ErrorCategory
from tor_llm_tool.models import OcrResult
from tor_llm_tool.ocr.base import OcrEngine


class RapidOcrEngine(OcrEngine):
    def __init__(self) -> None:
        self._engine = None

    def recognize(self, image: Image.Image) -> OcrResult:
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail="rapidocr がインストールされていません。",
                retryable=True,
            ) from exc

        if self._engine is None:
            try:
                self._engine = RapidOCR()
            except Exception as exc:  # noqa: BLE001
                raise AppError(
                    code="OCR_FAILED",
                    category=ErrorCategory.OCR,
                    message="OCR に失敗しました。",
                    detail=str(exc),
                    retryable=True,
                ) from exc

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = Path(tmp.name)
        try:
            image.save(path)
            result = self._engine(str(path))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail=str(exc),
                retryable=True,
            ) from exc
        finally:
            path.unlink(missing_ok=True)

        texts = [str(text) for text in getattr(result, "txts", ()) if str(text).strip()]
        scores = [float(score) for score in getattr(result, "scores", ()) if score is not None]
        confidence = sum(scores) / len(scores) if scores else None
        return OcrResult(text="\n".join(texts), confidence=confidence, detail=f"{len(texts)} lines")
