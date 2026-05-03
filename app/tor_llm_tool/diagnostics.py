from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter

from tor_llm_tool.settings import AppConfig


@dataclass(slots=True)
class DiagnosticEvent:
    kind: str
    message: str
    detail: str = ""
    elapsed_ms: int | None = None
    timestamp: datetime = field(default_factory=datetime.now)


class DiagnosticsLog:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.events: list[DiagnosticEvent] = []

    def add(self, kind: str, message: str, detail: str = "", elapsed_ms: int | None = None) -> None:
        if not self.config.logging.keep_diagnostics:
            return
        if self.config.logging.redact_sensitive_logs:
            detail = _redact(detail)
        self.events.append(DiagnosticEvent(kind, message, detail, elapsed_ms))
        max_items = max(1, self.config.logging.max_diagnostics)
        del self.events[:-max_items]

    def time_start(self) -> float:
        return perf_counter()

    def elapsed_ms(self, started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)


def _redact(text: str) -> str:
    if not text:
        return ""
    redacted = text
    for marker in ("Authorization:", "apiKey:", "api_key:", "Bearer "):
        if marker in redacted:
            redacted = redacted.replace(marker, f"{marker}[redacted]")
    return redacted
