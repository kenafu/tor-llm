from __future__ import annotations

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from tor_llm_tool.assistant import AssistantService
from tor_llm_tool.capture import capture_region
from tor_llm_tool.context import collect_context_at, extract_url_candidates
from tor_llm_tool.errors import AppError, ErrorCategory
from tor_llm_tool.models import AssistantRequest, CaptureContext, CaptureResult, OcrResult
from tor_llm_tool.ocr import create_ocr_engine
from tor_llm_tool.settings import AppConfig, save_config
from tor_llm_tool.ui.hotkey import GlobalHotkey
from tor_llm_tool.ui.image_utils import pil_to_pixmap
from tor_llm_tool.ui.region_selector import RegionSelector
from tor_llm_tool.ui.settings_dialog import SettingsDialog
from tor_llm_tool.ui.workers import FunctionWorker


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.capture_result: CaptureResult | None = None
        self.ocr_result = OcrResult(text="")
        self.thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("Tor LLM Support Tool")
        self.resize(1180, 760)
        if self.config.ui.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._build_ui()
        self._bind_shortcut()
        self._bind_global_hotkey()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        capture_action = QAction("Capture", self)
        capture_action.triggered.connect(self.start_region_selection)
        toolbar.addAction(capture_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        self.image_label = QLabel("Capture a screen region to begin")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumWidth(420)
        self.image_label.setStyleSheet("QLabel { background: #1f2328; color: #c9d1d9; }")

        self.task_combo = QComboBox()
        self.task_combo.addItem("Explain", "explain-region")
        self.task_combo.addItem("Translate", "translate-region")
        self.task_combo.addItem("Ask", "ask-region")
        self.task_combo.addItem("Clean OCR", "clean-ocr")
        index = self.task_combo.findData(self.config.ui.default_task)
        if index >= 0:
            self.task_combo.setCurrentIndex(index)

        self.send_image = QCheckBox("Image")
        self.send_image.setChecked(self.config.request.send_image)
        self.send_ocr = QCheckBox("OCR text")
        self.send_ocr.setChecked(self.config.request.send_ocr_text)
        self.send_context = QCheckBox("Context")
        self.send_context.setChecked(self.config.request.send_context)

        self.question = QLineEdit()
        self.question.setPlaceholderText("Question for selected region")

        self.app_name = QLineEdit()
        self.process_name = QLineEdit()
        self.window_title = QLineEdit()
        self.url_candidates = QLineEdit()

        self.ocr_text = QPlainTextEdit()
        self.ocr_text.setPlaceholderText("OCR text appears here")
        self.ocr_text.setMinimumHeight(180)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("LLM result appears here")

        run_button = QPushButton("Run")
        run_button.clicked.connect(self.run_assistant)
        rerun_ocr_button = QPushButton("Run OCR")
        rerun_ocr_button.clicked.connect(self.run_ocr)

        controls = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Task"))
        row1.addWidget(self.task_combo)
        row1.addWidget(self.send_image)
        row1.addWidget(self.send_ocr)
        row1.addWidget(self.send_context)
        row1.addWidget(rerun_ocr_button)
        row1.addWidget(run_button)
        controls.addLayout(row1)
        controls.addWidget(QLabel("Question"))
        controls.addWidget(self.question)
        controls.addWidget(QLabel("App"))
        controls.addWidget(self.app_name)
        controls.addWidget(QLabel("Process"))
        controls.addWidget(self.process_name)
        controls.addWidget(QLabel("Window title"))
        controls.addWidget(self.window_title)
        controls.addWidget(QLabel("URL candidates"))
        controls.addWidget(self.url_candidates)
        controls.addWidget(QLabel("OCR text"))
        controls.addWidget(self.ocr_text)
        controls.addWidget(QLabel("Result"))
        controls.addWidget(self.result, 1)

        right = QWidget()
        right.setLayout(controls)

        splitter = QSplitter()
        splitter.addWidget(self.image_label)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self.setStatusBar(QStatusBar())

    def _bind_shortcut(self) -> None:
        shortcut = QShortcut(QKeySequence(self.config.capture.hotkey), self)
        shortcut.activated.connect(self.start_region_selection)

    def _bind_global_hotkey(self) -> None:
        self.global_hotkey = GlobalHotkey(self.config.capture.hotkey)
        self.global_hotkey.activated.connect(self.start_region_selection)
        self.global_hotkey.failed.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
        self.global_hotkey.start()

    def start_region_selection(self) -> None:
        self.hide()
        self.selector = RegionSelector()
        self.selector.selected.connect(self._capture_selected_region)
        self.selector.cancelled.connect(self._on_capture_cancelled)
        self.selector.show()

    def _on_capture_cancelled(self) -> None:
        self.show()
        self.statusBar().showMessage("範囲選択をキャンセルしました。", 3000)

    def _capture_selected_region(self, rect) -> None:  # noqa: ANN001
        QTimer.singleShot(
            self.config.capture.capture_delay_ms,
            lambda: self._capture_after_overlay(rect.x(), rect.y(), rect.width(), rect.height()),
        )

    def _capture_after_overlay(self, x: int, y: int, width: int, height: int) -> None:
        try:
            context = collect_context_at(x + width // 2, y + height // 2)
            image = capture_region(x, y, width, height)
            self.capture_result = CaptureResult(image=image, context=context)
            self.show()
            self._show_capture()
            if self.config.ocr.auto_run_ocr:
                self.run_ocr()
        except Exception as exc:  # noqa: BLE001
            self.show()
            self._show_error(exc)

    def _show_capture(self) -> None:
        if self.capture_result is None:
            return
        pixmap = pil_to_pixmap(self.capture_result.image)
        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        context = self.capture_result.context
        self.app_name.setText(context.app_name)
        self.process_name.setText(context.process_name)
        self.window_title.setText(context.window_title)
        self.url_candidates.setText(", ".join(context.url_candidates))
        self.statusBar().showMessage("範囲を取得しました。", 3000)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        if self.capture_result is not None:
            self._show_capture()

    def run_ocr(self) -> None:
        if self.capture_result is None:
            self._show_error(
                AppError(
                    code="CAPTURE_FAILED",
                    category=ErrorCategory.CAPTURE,
                    message="先に範囲を選択してください。",
                    retryable=True,
                )
            )
            return
        self.statusBar().showMessage("OCR 実行中...")
        worker = FunctionWorker(self._recognize_ocr, self.capture_result.image)
        worker.signals.result.connect(self._on_ocr_result)
        worker.signals.error.connect(self._show_error)
        self.thread_pool.start(worker)

    def _recognize_ocr(self, image) -> OcrResult:  # noqa: ANN001
        engine = create_ocr_engine(self.config)
        return engine.recognize(image)

    def _on_ocr_result(self, result: OcrResult) -> None:
        self.ocr_result = result
        self.ocr_text.setPlainText(result.text)
        if self.capture_result is not None:
            urls = extract_url_candidates(result.text)
            self.capture_result.context.url_candidates = urls
            self.url_candidates.setText(", ".join(urls))
        if result.text.strip():
            self.statusBar().showMessage("OCR が完了しました。", 3000)
        else:
            self.statusBar().showMessage("OCR テキストは検出されませんでした。", 5000)

    def run_assistant(self) -> None:
        if self.capture_result is None:
            self._show_error(
                AppError(
                    code="CAPTURE_FAILED",
                    category=ErrorCategory.CAPTURE,
                    message="先に範囲を選択してください。",
                    retryable=True,
                )
            )
            return
        if not self.send_image.isChecked() and not self.send_ocr.isChecked():
            self._show_error(
                AppError(
                    code="INPUT_TOO_LARGE",
                    category=ErrorCategory.VALIDATION,
                    message="送信対象がありません。",
                    retryable=False,
                    user_action="Image または OCR text を有効にしてください。",
                )
            )
            return

        self.result.setPlainText("")
        self.statusBar().showMessage("LM Studio に送信中...")
        request = self._build_assistant_request()
        worker = FunctionWorker(AssistantService(self.config).run, request)
        worker.signals.result.connect(self._on_assistant_result)
        worker.signals.error.connect(self._show_error)
        self.thread_pool.start(worker)

    def _build_assistant_request(self) -> AssistantRequest:
        assert self.capture_result is not None
        context = CaptureContext(
            app_name=self.app_name.text().strip(),
            process_name=self.process_name.text().strip(),
            window_title=self.window_title.text().strip(),
            url_candidates=[
                item.strip() for item in self.url_candidates.text().split(",") if item.strip()
            ],
        )
        return AssistantRequest(
            task=self.task_combo.currentData(),
            ocr_text=self.ocr_text.toPlainText(),
            context=context,
            question=self.question.text(),
            image=self.capture_result.image,
            send_image=self.send_image.isChecked(),
            send_ocr_text=self.send_ocr.isChecked(),
            send_context=self.send_context.isChecked(),
            target_language=self.config.ui.target_language,
            explanation_level=self.config.ui.explanation_level,
        )

    def _on_assistant_result(self, text: str) -> None:
        self.result.setMarkdown(text)
        self.statusBar().showMessage("完了しました。", 3000)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.updated_config()
            save_config(self.config)
            self.statusBar().showMessage("設定を保存しました。", 3000)

    def _show_error(self, error: object) -> None:
        if isinstance(error, AppError):
            message = error.message
            if self.config.error.show_technical_details and error.detail:
                message += f"\n\n{error.detail}"
            if error.user_action:
                message += f"\n\n{error.user_action}"
        else:
            message = str(error)
        self.statusBar().showMessage(message, 6000)
        QMessageBox.warning(self, "Error", message)


def run_app(config: AppConfig) -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(config)
    window.show()
    return app.exec()
