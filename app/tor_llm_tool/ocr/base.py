from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from tor_llm_tool.models import OcrResult
from tor_llm_tool.settings import AppConfig


class OcrEngine(ABC):
    @abstractmethod
    def recognize(self, image: Image.Image) -> OcrResult:
        raise NotImplementedError


def create_ocr_engine(config: AppConfig) -> OcrEngine:
    if config.ocr.provider == "none":
        return NoopOcrEngine()
    if config.ocr.provider == "rapidocr":
        from .rapid import RapidOcrEngine

        return RapidOcrEngine()
    if config.ocr.provider == "tesseract":
        from .tesseract import TesseractOcrEngine

        return TesseractOcrEngine(config.ocr.languages)
    from .paddle import PaddleOcrEngine

    return PaddleOcrEngine(config.ocr.languages)


class NoopOcrEngine(OcrEngine):
    def recognize(self, image: Image.Image) -> OcrResult:
        return OcrResult(text="")
