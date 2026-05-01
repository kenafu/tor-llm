from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCategory(StrEnum):
    CAPTURE = "capture"
    OCR = "ocr"
    CONTEXT = "context"
    PROVIDER = "provider"
    MODEL = "model"
    SETTINGS = "settings"
    NETWORK = "network"
    VALIDATION = "validation"
    INTERNAL = "internal"


@dataclass(slots=True)
class AppError(Exception):
    code: str
    category: ErrorCategory
    message: str
    detail: str | None = None
    retryable: bool = False
    user_action: str | None = None

    def __str__(self) -> str:
        if self.detail:
            return f"{self.message} ({self.detail})"
        return self.message

