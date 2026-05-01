from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from PIL import Image


AssistantTask = Literal[
    "translate-region",
    "explain-region",
    "ask-region",
    "clean-ocr",
    "extract-structured",
]


@dataclass(slots=True)
class CaptureContext:
    app_name: str = ""
    process_name: str = ""
    window_title: str = ""
    url: str = ""
    url_candidates: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CaptureResult:
    image: Image.Image
    context: CaptureContext


@dataclass(slots=True)
class OcrResult:
    text: str
    confidence: float | None = None


@dataclass(slots=True)
class AssistantRequest:
    task: AssistantTask
    ocr_text: str
    context: CaptureContext
    question: str = ""
    image: Image.Image | None = None
    send_image: bool = True
    send_ocr_text: bool = True
    send_context: bool = True
    target_language: str = "ja"
    explanation_level: Literal["brief", "normal", "deep"] = "normal"

