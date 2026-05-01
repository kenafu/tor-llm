from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from tor_llm_tool.errors import AppError
from tor_llm_tool.providers import LmStudioProvider
from tor_llm_tool.settings import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config.model_copy(deep=True)

        self.base_url = QLineEdit(self.config.llm.base_url)
        self.api_key = QLineEdit(self.config.llm.api_key or "")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setEditText(self.config.llm.model)
        self.vision_model = QComboBox()
        self.vision_model.setEditable(True)
        self.vision_model.setEditText(self.config.llm.vision_model)
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
        model_row = QHBoxLayout()
        model_row.addWidget(self.model, 1)
        refresh_button = QPushButton("Refresh Models")
        refresh_button.clicked.connect(self.refresh_models)
        model_row.addWidget(refresh_button)

        vision_model_row = QHBoxLayout()
        vision_model_row.addWidget(self.vision_model, 1)
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self.test_connection)
        vision_model_row.addWidget(test_button)

        form.addRow("Model", model_row)
        form.addRow("Vision model", vision_model_row)
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

        self.status = QLabel("")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addLayout(buttons)

    def updated_config(self) -> AppConfig:
        config = self.config.model_copy(deep=True)
        config.llm.base_url = self.base_url.text().strip()
        config.llm.api_key = self.api_key.text().strip() or None
        config.llm.model = self.model.currentText().strip()
        config.llm.vision_model = self.vision_model.currentText().strip()
        config.llm.timeout_sec = int(self.timeout.value())
        config.capture.hotkey = self.hotkey.text().strip()
        config.ui.target_language = self.target_language.text().strip() or "ja"
        config.request.send_image = self.send_image.isChecked()
        config.request.send_context = self.send_context.isChecked()
        return config

    def refresh_models(self) -> None:
        try:
            models = LmStudioProvider(self.updated_config()).list_models()
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)
            return

        current_model = self.model.currentText().strip()
        current_vision_model = self.vision_model.currentText().strip()
        self.model.clear()
        self.vision_model.clear()
        self.model.addItems(models)
        self.vision_model.addItems([""] + models)
        self.model.setEditText(current_model if current_model else (models[0] if models else ""))
        self.vision_model.setEditText(current_vision_model)
        self.status.setText(f"Loaded {len(models)} model(s).")

    def test_connection(self) -> None:
        try:
            models = LmStudioProvider(self.updated_config()).list_models()
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)
            return

        message = f"Connected to LM Studio. {len(models)} model(s) available."
        self.status.setText(message)
        QMessageBox.information(self, "Connection OK", message)

    def _show_error(self, error: object) -> None:
        if isinstance(error, AppError):
            message = error.message
            if error.detail:
                message += f"\n\n{error.detail}"
            if error.user_action:
                message += f"\n\n{error.user_action}"
        else:
            message = str(error)
        self.status.setText(message)
        QMessageBox.warning(self, "Connection Error", message)
