from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget

from tor_llm_tool.settings.config import PromptConfig


class PromptTemplatesDialog(QDialog):
    def __init__(self, prompts: PromptConfig, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Prompt Templates")
        self.resize(760, 560)
        self.prompts = prompts.model_copy(deep=True)
        self.editors: dict[str, QPlainTextEdit] = {}

        tabs = QTabWidget()
        self._add_tab(tabs, "System", "system", self.prompts.system)
        self._add_tab(tabs, "Translate", "translate_region", self.prompts.translate_region)
        self._add_tab(tabs, "Explain", "explain_region", self.prompts.explain_region)
        self._add_tab(tabs, "Ask", "ask_region", self.prompts.ask_region)
        self._add_tab(tabs, "Clean OCR", "clean_ocr", self.prompts.clean_ocr)
        self._add_tab(tabs, "Structured", "extract_structured", self.prompts.extract_structured)

        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self.reset_defaults)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addWidget(reset_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addLayout(buttons)

    def _add_tab(self, tabs: QTabWidget, title: str, key: str, text: str) -> None:
        editor = QPlainTextEdit()
        editor.setPlainText(text)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.editors[key] = editor

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(editor)
        tabs.addTab(page, title)

    def updated_prompts(self) -> PromptConfig:
        return PromptConfig(
            system=self.editors["system"].toPlainText(),
            translate_region=self.editors["translate_region"].toPlainText(),
            explain_region=self.editors["explain_region"].toPlainText(),
            ask_region=self.editors["ask_region"].toPlainText(),
            clean_ocr=self.editors["clean_ocr"].toPlainText(),
            extract_structured=self.editors["extract_structured"].toPlainText(),
        )

    def reset_defaults(self) -> None:
        defaults = PromptConfig()
        self.editors["system"].setPlainText(defaults.system)
        self.editors["translate_region"].setPlainText(defaults.translate_region)
        self.editors["explain_region"].setPlainText(defaults.explain_region)
        self.editors["ask_region"].setPlainText(defaults.ask_region)
        self.editors["clean_ocr"].setPlainText(defaults.clean_ocr)
        self.editors["extract_structured"].setPlainText(defaults.extract_structured)
