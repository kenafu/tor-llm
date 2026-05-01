from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


CONFIG_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "tor-llm-tool"
CONFIG_PATH = CONFIG_DIR / "config.yaml"


class ConfigBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class LlmConfig(ConfigBase):
    provider: Literal["lmstudio", "ollama", "llama-cpp", "openai-compatible"] = "lmstudio"
    base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="baseUrl")
    api_key: str | None = Field(default=None, alias="apiKey")
    model: str = ""
    vision_model: str = Field(default="", alias="visionModel")
    timeout_sec: int = Field(default=120, alias="timeoutSec")
    stream: bool = True


class RequestConfig(ConfigBase):
    send_image: bool = Field(default=True, alias="sendImage")
    send_ocr_text: bool = Field(default=True, alias="sendOcrText")
    send_context: bool = Field(default=True, alias="sendContext")
    confirm_before_send: bool = Field(default=True, alias="confirmBeforeSend")


class OcrConfig(ConfigBase):
    provider: Literal["rapidocr", "paddleocr", "tesseract", "none"] = "rapidocr"
    languages: list[str] = Field(default_factory=lambda: ["ja", "en"])
    auto_run_ocr: bool = Field(default=True, alias="autoRunOcr")
    preprocess_image: bool = Field(default=True, alias="preprocessImage")
    confidence_visible: bool = Field(default=False, alias="confidenceVisible")


class CaptureConfig(ConfigBase):
    hotkey: str = "Ctrl+Shift+Space"
    include_cursor: bool = Field(default=False, alias="includeCursor")
    multi_monitor: bool = Field(default=True, alias="multiMonitor")
    capture_delay_ms: int = Field(default=100, alias="captureDelayMs")
    max_image_long_edge: int = Field(default=1600, alias="maxImageLongEdge")
    image_format: Literal["png", "jpeg"] = Field(default="png", alias="imageFormat")
    jpeg_quality: int = Field(default=90, alias="jpegQuality")


class ContextConfig(ConfigBase):
    capture_app_name: bool = Field(default=True, alias="captureAppName")
    capture_process_name: bool = Field(default=True, alias="captureProcessName")
    capture_window_title: bool = Field(default=True, alias="captureWindowTitle")
    extract_urls_from_ocr: bool = Field(default=True, alias="extractUrlsFromOcr")
    use_accessibility_for_url: bool = Field(default=False, alias="useAccessibilityForUrl")
    editable_before_send: bool = Field(default=True, alias="editableBeforeSend")


class UiConfig(ConfigBase):
    theme: Literal["system", "light", "dark"] = "system"
    default_task: Literal[
        "translate-region",
        "explain-region",
        "ask-region",
        "clean-ocr",
    ] = Field(default="explain-region", alias="defaultTask")
    target_language: str = Field(default="ja", alias="targetLanguage")
    explanation_level: Literal["brief", "normal", "deep"] = Field(
        default="normal", alias="explanationLevel"
    )
    result_format: Literal["markdown", "plain"] = Field(default="markdown", alias="resultFormat")
    always_on_top: bool = Field(default=True, alias="alwaysOnTop")


class StorageConfig(ConfigBase):
    save_history: bool = Field(default=False, alias="saveHistory")
    save_screenshots: bool = Field(default=False, alias="saveScreenshots")
    save_ocr_text: bool = Field(default=False, alias="saveOcrText")


class LoggingConfig(ConfigBase):
    level: Literal["error", "info", "debug"] = "error"
    redact_sensitive_logs: bool = Field(default=True, alias="redactSensitiveLogs")


class ErrorConfig(ConfigBase):
    show_technical_details: bool = Field(default=False, alias="showTechnicalDetails")
    log_level: Literal["error", "info", "debug"] = Field(default="error", alias="logLevel")
    redact_sensitive_logs: bool = Field(default=True, alias="redactSensitiveLogs")
    auto_retry_provider_connection: bool = Field(
        default=False, alias="autoRetryProviderConnection"
    )
    max_provider_retries: int = Field(default=1, alias="maxProviderRetries")
    retry_backoff_ms: int = Field(default=800, alias="retryBackoffMs")


class AppConfig(ConfigBase):
    llm: LlmConfig = Field(default_factory=LlmConfig)
    request: RequestConfig = Field(default_factory=RequestConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    error: ErrorConfig = Field(default_factory=ErrorConfig)


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    if not path.exists():
        return AppConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    config = AppConfig.model_validate(data)
    if config.ocr.provider == "paddleocr":
        config.ocr.provider = "rapidocr"
    return config


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(by_alias=True, exclude_none=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
