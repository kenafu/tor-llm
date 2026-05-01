from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from tor_llm_tool.settings import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config.model_copy(deep=True)

        self.base_url = QLineEdit(self.config.llm.base_url)
        self.api_key = QLineEdit(self.config.llm.api_key or "")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.model = QLineEdit(self.config.llm.model)
        self.vision_model = QLineEdit(self.config.llm.vision_model)
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 600)
        self.timeout.setValue(self.config.llm.timeout_sec)

        self.hotkey = QLineEdit(self.config.capture.hotkey)
        self.target_language = QLineEdit(self.config.ui.target_language)
        self.send_image = QCheckBox()
        self.send_image.setChecked(self.config.request.send_image)
        self.send_context = QCheckBox()
        self.send_context.setChecked(self.config.request.send_context)

        form = QFormLayout()
        form.addRow("Base URL", self.base_url)
        form.addRow("API key", self.api_key)
        form.addRow("Model", self.model)
        form.addRow("Vision model", self.vision_model)
        form.addRow("Timeout sec", self.timeout)
        form.addRow("Hotkey", self.hotkey)
        form.addRow("Target language", self.target_language)
        form.addRow("Send image", self.send_image)
        form.addRow("Send context", self.send_context)

        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def updated_config(self) -> AppConfig:
        config = self.config.model_copy(deep=True)
        config.llm.base_url = self.base_url.text().strip()
        config.llm.api_key = self.api_key.text().strip() or None
        config.llm.model = self.model.text().strip()
        config.llm.vision_model = self.vision_model.text().strip()
        config.llm.timeout_sec = int(self.timeout.value())
        config.capture.hotkey = self.hotkey.text().strip()
        config.ui.target_language = self.target_language.text().strip() or "ja"
        config.request.send_image = self.send_image.isChecked()
        config.request.send_context = self.send_context.isChecked()
        return config

