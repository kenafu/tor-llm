from __future__ import annotations

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
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
from tor_llm_tool.assistant.image import estimate_prepared_image
from tor_llm_tool.capture import capture_region
from tor_llm_tool.context import collect_context_at, extract_url_candidates
from tor_llm_tool.diagnostics import DiagnosticsLog
from tor_llm_tool.errors import AppError, ErrorCategory
from tor_llm_tool.models import (
    AssistantRequest,
    CaptureContext,
    CaptureResult,
    ConversationTurn,
    OcrResult,
)
from tor_llm_tool.ocr import create_ocr_engine
from tor_llm_tool.ocr.preprocess import preprocess_for_ocr
from tor_llm_tool.settings import AppConfig, save_config
from tor_llm_tool.ui.hotkey import GlobalHotkey
from tor_llm_tool.ui.crop_adjust_dialog import CropAdjustDialog
from tor_llm_tool.ui.diagnostics_dialog import DiagnosticsDialog
from tor_llm_tool.ui.image_utils import pil_to_pixmap
from tor_llm_tool.ui.region_selector import RegionSelector
from tor_llm_tool.ui.settings_dialog import SettingsDialog
from tor_llm_tool.ui.workers import FunctionWorker, StreamWorker


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.capture_result: CaptureResult | None = None
        self.ocr_result = OcrResult(text="")
        self.conversation_turns: list[ConversationTurn] = []
        self.capture_history: list[CaptureResult] = []
        self.question_history: list[str] = []
        self.active_stream_worker: StreamWorker | None = None
        self.pending_request: AssistantRequest | None = None
        self.current_response_chunks: list[str] = []
        self.assistant_started_at: float | None = None
        self.diagnostics = DiagnosticsLog(config)
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

        diagnostics_action = QAction("Diagnostics", self)
        diagnostics_action.triggered.connect(self.open_diagnostics)
        toolbar.addAction(diagnostics_action)

        self.image_label = QLabel("Capture a screen region to begin")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumWidth(420)
        self.image_label.setStyleSheet("QLabel { background: #1f2328; color: #c9d1d9; }")

        self.task_combo = QComboBox()
        self._populate_task_combo()

        self.send_image = QCheckBox("Image")
        self.send_image.setChecked(self.config.request.send_image)
        self.send_ocr = QCheckBox("OCR text")
        self.send_ocr.setChecked(self.config.request.send_ocr_text)
        self.send_context = QCheckBox("Context")
        self.send_context.setChecked(self.config.request.send_context)
        self.send_image.toggled.connect(self._update_send_summary)
        self.send_ocr.toggled.connect(self._update_send_summary)
        self.send_context.toggled.connect(self._update_send_summary)

        self.question = QLineEdit()
        self.question.setPlaceholderText("Question for selected region")
        self.question_history_combo = QComboBox()
        self.question_history_combo.addItem("Question history")
        self.question_history_combo.currentTextChanged.connect(self._restore_question)

        self.app_name = QLineEdit()
        self.process_name = QLineEdit()
        self.window_title = QLineEdit()
        self.url_candidates = QLineEdit()

        self.ocr_text = QPlainTextEdit()
        self.ocr_text.setPlaceholderText("OCR text appears here")
        self.ocr_text.setMinimumHeight(180)
        self.ocr_text.textChanged.connect(self._update_send_summary)
        self.ocr_stats = QLabel("OCR: 0 chars")
        self.send_summary = QLabel("")
        self.image_send_summary = QLabel("")

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("LLM result appears here")

        run_button = QPushButton("Run")
        run_button.clicked.connect(self.run_assistant)
        regenerate_button = QPushButton("Regenerate")
        regenerate_button.clicked.connect(self.run_assistant)
        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_assistant)
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_result)
        save_result_button = QPushButton("Save Result")
        save_result_button.clicked.connect(self.save_result)
        rerun_ocr_button = QPushButton("Run OCR")
        rerun_ocr_button.clicked.connect(self.run_ocr)
        adjust_crop_button = QPushButton("Adjust Crop")
        adjust_crop_button.clicked.connect(self.adjust_crop)
        new_chat_button = QPushButton("New Chat")
        new_chat_button.clicked.connect(self.new_chat)
        restore_capture_button = QPushButton("Restore Capture")
        restore_capture_button.clicked.connect(self.restore_capture)
        self.capture_history_combo = QComboBox()
        self.capture_history_combo.addItem("Recent captures")

        controls = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Task"))
        row1.addWidget(self.task_combo)
        row1.addWidget(self.send_image)
        row1.addWidget(self.send_ocr)
        row1.addWidget(self.send_context)
        row1.addWidget(adjust_crop_button)
        row1.addWidget(rerun_ocr_button)
        row1.addWidget(run_button)
        row1.addWidget(regenerate_button)
        row1.addWidget(stop_button)
        controls.addLayout(row1)
        row_history = QHBoxLayout()
        row_history.addWidget(self.capture_history_combo, 1)
        row_history.addWidget(restore_capture_button)
        row_history.addWidget(new_chat_button)
        controls.addLayout(row_history)
        controls.addWidget(self.send_summary)
        controls.addWidget(self.image_send_summary)
        controls.addWidget(QLabel("Question"))
        controls.addWidget(self.question)
        controls.addWidget(self.question_history_combo)
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
        controls.addWidget(self.ocr_stats)
        controls.addWidget(QLabel("Result"))
        result_buttons = QHBoxLayout()
        result_buttons.addWidget(copy_button)
        result_buttons.addWidget(save_result_button)
        result_buttons.addStretch(1)
        controls.addLayout(result_buttons)
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
        self._update_send_summary()

    def _populate_task_combo(self) -> None:
        current = self.task_combo.currentData() if self.task_combo.count() else self.config.ui.default_task
        self.task_combo.clear()
        for preset in self.config.task_presets:
            if preset.enabled:
                self.task_combo.addItem(preset.label, preset.task_id)
        if self.task_combo.count() == 0:
            self.task_combo.addItem("Explain", "explain-region")
        index = self.task_combo.findData(current)
        if index < 0:
            index = self.task_combo.findData(self.config.ui.default_task)
        if index >= 0:
            self.task_combo.setCurrentIndex(index)

    def _bind_shortcut(self) -> None:
        self.local_shortcut = QShortcut(QKeySequence(self.config.capture.hotkey), self)
        self.local_shortcut.activated.connect(self.start_region_selection)

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
            pad = 80
            source_x = x - pad
            source_y = y - pad
            source_width = width + pad * 2
            source_height = height + pad * 2
            try:
                source_image = capture_region(source_x, source_y, source_width, source_height)
                crop_box = (pad, pad, pad + width, pad + height)
                image = source_image.crop(crop_box)
            except AppError:
                image = capture_region(x, y, width, height)
                source_image = image
                crop_box = (0, 0, image.width, image.height)
            self.capture_result = CaptureResult(
                image=image,
                context=context,
                source_image=source_image,
                crop_box=crop_box,
            )
            self._add_capture_history(self.capture_result)
            self.new_chat(clear_result=False)
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
        self._update_send_summary()

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

    def adjust_crop(self) -> None:
        if self.capture_result is None or self.capture_result.source_image is None:
            self._show_error(
                AppError(
                    code="CAPTURE_FAILED",
                    category=ErrorCategory.CAPTURE,
                    message="先に範囲を選択してください。",
                    retryable=True,
                )
            )
            return
        crop_box = self.capture_result.crop_box or (
            0,
            0,
            self.capture_result.source_image.width,
            self.capture_result.source_image.height,
        )
        dialog = CropAdjustDialog(self.capture_result.source_image, crop_box, self)
        if dialog.exec():
            self.capture_result.image = dialog.cropped_image()
            self.capture_result.crop_box = dialog.crop_box()
            self._show_capture()
            if self.config.ocr.auto_run_ocr:
                self.run_ocr()

    def _recognize_ocr(self, image) -> OcrResult:  # noqa: ANN001
        engine = create_ocr_engine(self.config)
        return engine.recognize(preprocess_for_ocr(image, self.config))

    def _on_ocr_result(self, result: OcrResult) -> None:
        self.ocr_result = result
        self.ocr_text.setPlainText(result.text)
        confidence = f", confidence {result.confidence:.2f}" if result.confidence is not None else ""
        detail = f", {result.detail}" if result.detail else ""
        self.ocr_stats.setText(f"OCR: {len(result.text)} chars{confidence}{detail}")
        self.diagnostics.add("ocr", "OCR completed", self.ocr_stats.text())
        if self.capture_result is not None:
            urls = extract_url_candidates(result.text)
            self.capture_result.context.url_candidates = urls
            self.url_candidates.setText(", ".join(urls))
        if result.text.strip():
            self.statusBar().showMessage("OCR が完了しました。", 3000)
        else:
            self.statusBar().showMessage("OCR テキストは検出されませんでした。", 5000)
        self._update_send_summary()

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
        self.statusBar().showMessage("LLM に送信中...")
        request = self._build_assistant_request()
        self.pending_request = request
        self.current_response_chunks = []
        self.assistant_started_at = self.diagnostics.time_start()
        self._add_question_history(request.question)
        self.diagnostics.add("request", "Sending request", self.send_summary.text())
        service = AssistantService(self.config)
        if self.config.llm.stream:
            worker = StreamWorker(service.stream, request)
            self.active_stream_worker = worker
            worker.signals.result.connect(self._append_assistant_chunk)
            worker.signals.finished.connect(self._on_assistant_finished)
        else:
            worker = FunctionWorker(service.run, request)
            worker.signals.result.connect(self._on_assistant_result)
            worker.signals.finished.connect(self._on_assistant_finished)
        worker.signals.error.connect(self._show_error)
        self.thread_pool.start(worker)

    def _build_assistant_request(self) -> AssistantRequest:
        assert self.capture_result is not None
        context = CaptureContext(
            app_name=self.app_name.text().strip() if self.config.request.send_app_name else "",
            process_name=self.process_name.text().strip()
            if self.config.request.send_process_name
            else "",
            window_title=self.window_title.text().strip()
            if self.config.request.send_window_title
            else "",
            url_candidates=[
                item.strip() for item in self.url_candidates.text().split(",") if item.strip()
            ]
            if self.config.request.send_urls
            else [],
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
            previous_turns=list(self.conversation_turns),
        )

    def _on_assistant_result(self, text: str) -> None:
        if self.config.ui.result_format == "markdown":
            self.result.setMarkdown(text)
        else:
            self.result.setPlainText(text)
        self.current_response_chunks = [text]
        self.statusBar().showMessage("完了しました。", 3000)

    def _append_assistant_chunk(self, chunk: str) -> None:
        self.current_response_chunks.append(chunk)
        self.result.moveCursor(QTextCursor.MoveOperation.End)
        self.result.insertPlainText(chunk)
        self.result.moveCursor(QTextCursor.MoveOperation.End)

    def _on_assistant_finished(self) -> None:
        text = "".join(self.current_response_chunks).strip()
        if text and self.pending_request is not None:
            if self.config.ui.result_format == "markdown":
                self.result.setMarkdown(text)
            self.conversation_turns.append(
                ConversationTurn(
                    question=self.pending_request.question,
                    answer=text,
                    task=self.pending_request.task,
                )
            )
            del self.conversation_turns[:-12]
        elapsed = (
            self.diagnostics.elapsed_ms(self.assistant_started_at)
            if self.assistant_started_at is not None
            else None
        )
        self.diagnostics.add("response", "Assistant completed", f"{len(text)} chars", elapsed)
        self.active_stream_worker = None
        self.statusBar().showMessage("完了しました。", 3000)

    def stop_assistant(self) -> None:
        if self.active_stream_worker is not None:
            self.active_stream_worker.cancel()
            self.diagnostics.add("response", "Assistant stream cancelled")
            self.statusBar().showMessage("停止しました。", 3000)

    def copy_result(self) -> None:
        QApplication.clipboard().setText(self.result.toPlainText())
        self.statusBar().showMessage("結果をコピーしました。", 3000)

    def save_result(self) -> None:
        path, _selected = QFileDialog.getSaveFileName(
            self, "Save Result", "llm-result.md", "Markdown files (*.md);;Text files (*.txt)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as file:
            file.write(self.result.toPlainText())
        self.statusBar().showMessage("結果を保存しました。", 3000)

    def _update_send_summary(self) -> None:
        enabled = []
        if self.send_image.isChecked():
            enabled.append("image")
        if self.send_ocr.isChecked():
            enabled.append(f"OCR text ({len(self.ocr_text.toPlainText())} chars)")
        if self.send_context.isChecked():
            enabled.append("context")
        self.send_summary.setText("Sending: " + (", ".join(enabled) if enabled else "nothing"))
        if self.capture_result is not None and self.send_image.isChecked():
            mime, size_bytes, dimensions = estimate_prepared_image(
                self.capture_result.image,
                self.config.capture.max_image_long_edge,
                self.config.capture.image_format,
                self.config.capture.jpeg_quality,
            )
            self.image_send_summary.setText(
                f"Prepared image: {dimensions[0]}x{dimensions[1]}, {mime}, {size_bytes // 1024} KiB"
            )
        else:
            self.image_send_summary.setText("")

    def _add_capture_history(self, capture: CaptureResult) -> None:
        self.capture_history.insert(0, capture)
        del self.capture_history[10:]
        self.capture_history_combo.blockSignals(True)
        self.capture_history_combo.clear()
        self.capture_history_combo.addItem("Recent captures")
        for index, item in enumerate(self.capture_history, start=1):
            title = item.context.window_title or item.context.app_name or "capture"
            self.capture_history_combo.addItem(f"{index}: {title[:60]}", index - 1)
        self.capture_history_combo.blockSignals(False)

    def restore_capture(self) -> None:
        index = self.capture_history_combo.currentData()
        if index is None:
            return
        self.capture_result = self.capture_history[int(index)]
        self._show_capture()
        self._update_send_summary()

    def _add_question_history(self, question: str) -> None:
        question = question.strip()
        if not question:
            return
        if question in self.question_history:
            self.question_history.remove(question)
        self.question_history.insert(0, question)
        del self.question_history[20:]
        self.question_history_combo.blockSignals(True)
        self.question_history_combo.clear()
        self.question_history_combo.addItem("Question history")
        self.question_history_combo.addItems(self.question_history)
        self.question_history_combo.blockSignals(False)

    def _restore_question(self, text: str) -> None:
        if text and text != "Question history":
            self.question.setText(text)

    def new_chat(self, clear_result: bool = True) -> None:
        self.conversation_turns.clear()
        if clear_result:
            self.result.clear()
        self.statusBar().showMessage("会話履歴をクリアしました。", 3000)

    def open_diagnostics(self) -> None:
        DiagnosticsDialog(self.diagnostics, self).exec()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            old_hotkey = self.config.capture.hotkey
            self.config = dialog.updated_config()
            self.diagnostics.config = self.config
            save_config(self.config)
            self._populate_task_combo()
            self.send_image.setChecked(self.config.request.send_image)
            self.send_ocr.setChecked(self.config.request.send_ocr_text)
            self.send_context.setChecked(self.config.request.send_context)
            if self.config.capture.hotkey != old_hotkey:
                self.local_shortcut.setKey(QKeySequence(self.config.capture.hotkey))
                self.global_hotkey.restart(self.config.capture.hotkey)
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
        self.diagnostics.add("error", message, str(error))
        self.statusBar().showMessage(message, 6000)
        QMessageBox.warning(self, "Error", message)


def run_app(config: AppConfig) -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(config)
    window.show()
    return app.exec()
