from __future__ import annotations

import tempfile
from pathlib import Path

import inspect

from PIL import Image

from tor_llm_tool.errors import AppError, ErrorCategory
from tor_llm_tool.models import OcrResult
from tor_llm_tool.ocr.base import OcrEngine


class PaddleOcrEngine(OcrEngine):
    def __init__(self, languages: list[str]) -> None:
        self.languages = languages
        self._ocr = None

    def recognize(self, image: Image.Image) -> OcrResult:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail="paddleocr がインストールされていません。",
                retryable=True,
                user_action="OCR provider を tesseract または none に変更するか、paddleocr を導入してください。",
            ) from exc

        if self._ocr is None:
            lang = "japan" if "ja" in self.languages else "en"
            self._ocr = self._create_ocr(PaddleOCR, lang)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = Path(tmp.name)
        try:
            image.save(path)
            result = self._run_ocr(path)
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)
            if "paddlepaddle" in detail.lower():
                detail = "paddlepaddle がインストールされていません。`.[ocr]` を再インストールしてください。"
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail=detail,
                retryable=True,
            ) from exc
        finally:
            path.unlink(missing_ok=True)

        lines, confidences = _parse_paddle_result(result)
        confidence = sum(confidences) / len(confidences) if confidences else None
        return OcrResult(text="\n".join(lines), confidence=confidence)

    def _create_ocr(self, paddle_ocr_cls, lang: str):  # noqa: ANN001
        signature = inspect.signature(paddle_ocr_cls)
        params = signature.parameters
        kwargs = {"lang": lang}

        if "use_textline_orientation" in params:
            kwargs["use_textline_orientation"] = True
            kwargs["use_doc_orientation_classify"] = False
            kwargs["use_doc_unwarping"] = False
        else:
            kwargs["use_angle_cls"] = True
            if "show_log" in params:
                kwargs["show_log"] = False

        try:
            return paddle_ocr_cls(**kwargs)
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)
            if "paddlepaddle" in detail.lower():
                detail = "paddlepaddle がインストールされていません。`.[ocr]` を再インストールしてください。"
            raise AppError(
                code="OCR_FAILED",
                category=ErrorCategory.OCR,
                message="OCR に失敗しました。",
                detail=detail,
                retryable=True,
            ) from exc

    def _run_ocr(self, path: Path):  # noqa: ANN001
        if hasattr(self._ocr, "predict"):
            return self._ocr.predict(str(path))
        return self._ocr.ocr(str(path), cls=True)


def _parse_paddle_result(result) -> tuple[list[str], list[float]]:  # noqa: ANN001
    lines: list[str] = []
    confidences: list[float] = []

    for item in _walk_items(result):
        if isinstance(item, dict):
            for key in ("rec_texts", "texts"):
                texts = item.get(key)
                if isinstance(texts, list):
                    lines.extend(str(text) for text in texts if str(text).strip())
            for key in ("rec_scores", "scores"):
                scores = item.get(key)
                if isinstance(scores, list):
                    confidences.extend(float(score) for score in scores if score is not None)
            continue

        if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], (list, tuple)):
            text = str(item[1][0])
            conf = float(item[1][1]) if len(item[1]) > 1 else None
            if text.strip():
                lines.append(text)
            if conf is not None:
                confidences.append(conf)

    return lines, confidences


def _walk_items(value):  # noqa: ANN001
    if isinstance(value, dict):
        yield value
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_items(item)
        return
    yield value
