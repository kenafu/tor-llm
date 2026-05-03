from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QPlainTextEdit, QVBoxLayout

from tor_llm_tool.diagnostics import DiagnosticsLog


class DiagnosticsDialog(QDialog):
    def __init__(self, diagnostics: DiagnosticsLog, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Diagnostics")
        self.resize(820, 560)
        self.diagnostics = diagnostics

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(refresh_button)
        buttons.addWidget(clear_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        lines = []
        for event in self.diagnostics.events:
            elapsed = f" {event.elapsed_ms}ms" if event.elapsed_ms is not None else ""
            lines.append(
                f"[{event.timestamp:%Y-%m-%d %H:%M:%S}] {event.kind}{elapsed}: {event.message}"
            )
            if event.detail:
                lines.append(event.detail)
        self.text.setPlainText("\n".join(lines))

    def clear(self) -> None:
        self.diagnostics.events.clear()
        self.refresh()
