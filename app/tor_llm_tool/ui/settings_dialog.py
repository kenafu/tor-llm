from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
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
from tor_llm_tool.settings import AppConfig, load_config, save_config
from tor_llm_tool.ui.prompt_templates_dialog import PromptTemplatesDialog
from tor_llm_tool.ui.task_presets_dialog import TaskPresetsDialog


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config.model_copy(deep=True)

        self.provider = QComboBox()
        self.provider.addItem("LM Studio", "lmstudio")
        self.provider.addItem("Ollama OpenAI API", "ollama")
        self.provider.addItem("llama.cpp server", "llama-cpp")
        self.provider.addItem("OpenAI compatible", "openai-compatible")
        provider_index = self.provider.findData(self.config.llm.provider)
        if provider_index >= 0:
            self.provider.setCurrentIndex(provider_index)
        self.provider.currentIndexChanged.connect(self.apply_provider_default)

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
        self.stream = QCheckBox()
        self.stream.setChecked(self.config.llm.stream)

        self.hotkey = QLineEdit(self.config.capture.hotkey)
        self.target_language = QLineEdit(self.config.ui.target_language)
        self.ocr_languages = QLineEdit(", ".join(self.config.ocr.languages))
        self.preprocess_ocr = QCheckBox()
        self.preprocess_ocr.setChecked(self.config.ocr.preprocess_image)
        self.preprocess_grayscale = QCheckBox()
        self.preprocess_grayscale.setChecked(self.config.ocr.preprocess_grayscale)
        self.preprocess_contrast = QCheckBox()
        self.preprocess_contrast.setChecked(self.config.ocr.preprocess_contrast)
        self.preprocess_sharpen = QCheckBox()
        self.preprocess_sharpen.setChecked(self.config.ocr.preprocess_sharpen)
        self.send_image = QCheckBox()
        self.send_image.setChecked(self.config.request.send_image)
        self.send_ocr = QCheckBox()
        self.send_ocr.setChecked(self.config.request.send_ocr_text)
        self.send_context = QCheckBox()
        self.send_context.setChecked(self.config.request.send_context)
        self.send_app_name = QCheckBox()
        self.send_app_name.setChecked(self.config.request.send_app_name)
        self.send_process_name = QCheckBox()
        self.send_process_name.setChecked(self.config.request.send_process_name)
        self.send_window_title = QCheckBox()
        self.send_window_title.setChecked(self.config.request.send_window_title)
        self.send_urls = QCheckBox()
        self.send_urls.setChecked(self.config.request.send_urls)
        self.max_image_long_edge = QSpinBox()
        self.max_image_long_edge.setRange(256, 4096)
        self.max_image_long_edge.setValue(self.config.capture.max_image_long_edge)
        self.image_format = QComboBox()
        self.image_format.addItems(["png", "jpeg"])
        self.image_format.setCurrentText(self.config.capture.image_format)
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(30, 100)
        self.jpeg_quality.setValue(self.config.capture.jpeg_quality)
        self.prompt_templates = self.config.prompts.model_copy(deep=True)
        self.task_presets = [preset.model_copy(deep=True) for preset in self.config.task_presets]

        form = QFormLayout()
        form.addRow("Provider", self.provider)
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
        form.addRow("Stream response", self.stream)
        form.addRow("Hotkey", self.hotkey)
        form.addRow("Target language", self.target_language)
        form.addRow("OCR languages", self.ocr_languages)
        form.addRow("OCR preprocess", self.preprocess_ocr)
        form.addRow("OCR grayscale", self.preprocess_grayscale)
        form.addRow("OCR contrast", self.preprocess_contrast)
        form.addRow("OCR sharpen", self.preprocess_sharpen)
        form.addRow("Send image", self.send_image)
        form.addRow("Send OCR text", self.send_ocr)
        form.addRow("Send context", self.send_context)
        form.addRow("Send app name", self.send_app_name)
        form.addRow("Send process name", self.send_process_name)
        form.addRow("Send window title", self.send_window_title)
        form.addRow("Send URLs", self.send_urls)
        form.addRow("Max image long edge", self.max_image_long_edge)
        form.addRow("Image format", self.image_format)
        form.addRow("JPEG quality", self.jpeg_quality)

        prompts_button = QPushButton("Edit Prompt Templates")
        prompts_button.clicked.connect(self.edit_prompts)
        form.addRow("Prompts", prompts_button)

        presets_button = QPushButton("Edit Task Presets")
        presets_button.clicked.connect(self.edit_task_presets)
        form.addRow("Task presets", presets_button)

        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        import_button = QPushButton("Import")
        export_button = QPushButton("Export")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        import_button.clicked.connect(self.import_config)
        export_button.clicked.connect(self.export_config)

        buttons = QHBoxLayout()
        buttons.addWidget(import_button)
        buttons.addWidget(export_button)
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
        config.llm.provider = self.provider.currentData()
        config.llm.base_url = self.base_url.text().strip()
        config.llm.api_key = self.api_key.text().strip() or None
        config.llm.model = self.model.currentText().strip()
        config.llm.vision_model = self.vision_model.currentText().strip()
        config.llm.timeout_sec = int(self.timeout.value())
        config.llm.stream = self.stream.isChecked()
        config.capture.hotkey = self.hotkey.text().strip()
        config.ui.target_language = self.target_language.text().strip() or "ja"
        config.ocr.languages = [
            item.strip() for item in self.ocr_languages.text().split(",") if item.strip()
        ] or ["ja", "en"]
        config.ocr.preprocess_image = self.preprocess_ocr.isChecked()
        config.ocr.preprocess_grayscale = self.preprocess_grayscale.isChecked()
        config.ocr.preprocess_contrast = self.preprocess_contrast.isChecked()
        config.ocr.preprocess_sharpen = self.preprocess_sharpen.isChecked()
        config.request.send_image = self.send_image.isChecked()
        config.request.send_ocr_text = self.send_ocr.isChecked()
        config.request.send_context = self.send_context.isChecked()
        config.request.send_app_name = self.send_app_name.isChecked()
        config.request.send_process_name = self.send_process_name.isChecked()
        config.request.send_window_title = self.send_window_title.isChecked()
        config.request.send_urls = self.send_urls.isChecked()
        config.capture.max_image_long_edge = int(self.max_image_long_edge.value())
        config.capture.image_format = self.image_format.currentText()
        config.capture.jpeg_quality = int(self.jpeg_quality.value())
        config.prompts = self.prompt_templates.model_copy(deep=True)
        config.task_presets = [preset.model_copy(deep=True) for preset in self.task_presets]
        return config

    def apply_provider_default(self) -> None:
        defaults = {
            "lmstudio": "http://127.0.0.1:1234/v1",
            "ollama": "http://127.0.0.1:11434/v1",
            "llama-cpp": "http://127.0.0.1:8080/v1",
            "openai-compatible": self.base_url.text().strip() or "http://127.0.0.1:1234/v1",
        }
        provider = self.provider.currentData()
        if not self.base_url.text().strip() or self.base_url.text().strip() in defaults.values():
            self.base_url.setText(defaults[provider])

    def edit_prompts(self) -> None:
        dialog = PromptTemplatesDialog(self.prompt_templates, self)
        if dialog.exec():
            self.prompt_templates = dialog.updated_prompts()
            self.status.setText("Prompt templates updated. Save settings to persist them.")

    def edit_task_presets(self) -> None:
        dialog = TaskPresetsDialog(self.task_presets, self)
        if dialog.exec():
            self.task_presets = dialog.updated_presets()
            self.status.setText("Task presets updated. Save settings to persist them.")

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

        message = f"Connected. {len(models)} model(s) available."
        self.status.setText(message)
        QMessageBox.information(self, "Connection OK", message)

    def import_config(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "YAML files (*.yaml *.yml);;All files (*)"
        )
        if not path:
            return
        self.config = load_config(Path(path))
        self._apply_config_to_widgets()
        self.status.setText("Imported settings. Save to persist them.")
        QMessageBox.information(self, "Imported", "Settings imported. Save to persist them.")

    def export_config(self) -> None:
        path, _selected = QFileDialog.getSaveFileName(
            self, "Export Settings", "tor-llm-tool-config.yaml", "YAML files (*.yaml)"
        )
        if not path:
            return
        save_config(self.updated_config(), Path(path))
        self.status.setText("Settings exported.")

    def _apply_config_to_widgets(self) -> None:
        provider_index = self.provider.findData(self.config.llm.provider)
        if provider_index >= 0:
            self.provider.setCurrentIndex(provider_index)
        self.base_url.setText(self.config.llm.base_url)
        self.api_key.setText(self.config.llm.api_key or "")
        self.model.setEditText(self.config.llm.model)
        self.vision_model.setEditText(self.config.llm.vision_model)
        self.timeout.setValue(self.config.llm.timeout_sec)
        self.stream.setChecked(self.config.llm.stream)
        self.hotkey.setText(self.config.capture.hotkey)
        self.target_language.setText(self.config.ui.target_language)
        self.ocr_languages.setText(", ".join(self.config.ocr.languages))
        self.preprocess_ocr.setChecked(self.config.ocr.preprocess_image)
        self.preprocess_grayscale.setChecked(self.config.ocr.preprocess_grayscale)
        self.preprocess_contrast.setChecked(self.config.ocr.preprocess_contrast)
        self.preprocess_sharpen.setChecked(self.config.ocr.preprocess_sharpen)
        self.send_image.setChecked(self.config.request.send_image)
        self.send_ocr.setChecked(self.config.request.send_ocr_text)
        self.send_context.setChecked(self.config.request.send_context)
        self.send_app_name.setChecked(self.config.request.send_app_name)
        self.send_process_name.setChecked(self.config.request.send_process_name)
        self.send_window_title.setChecked(self.config.request.send_window_title)
        self.send_urls.setChecked(self.config.request.send_urls)
        self.max_image_long_edge.setValue(self.config.capture.max_image_long_edge)
        self.image_format.setCurrentText(self.config.capture.image_format)
        self.jpeg_quality.setValue(self.config.capture.jpeg_quality)
        self.prompt_templates = self.config.prompts.model_copy(deep=True)
        self.task_presets = [preset.model_copy(deep=True) for preset in self.config.task_presets]

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
