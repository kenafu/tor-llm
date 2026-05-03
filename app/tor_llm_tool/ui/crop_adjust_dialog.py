from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from tor_llm_tool.ui.image_utils import pil_to_pixmap


class CropPreviewWidget(QLabel):
    crop_changed = Signal(tuple)

    def __init__(self, source_image: Image.Image) -> None:
        super().__init__()
        self.source_image = source_image
        self.crop_box = (0, 0, source_image.width, source_image.height)
        self.drag_start: QPoint | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(360)
        self.setStyleSheet("QLabel { background: #1f2328; }")
        self.setMouseTracking(True)
        self._pixmap = pil_to_pixmap(source_image)

    def set_crop_box(self, crop_box: tuple[int, int, int, int]) -> None:
        self.crop_box = crop_box
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        painter = QPainter(self)
        target = self._target_rect()
        painter.drawPixmap(target, self._pixmap)
        rect = self._image_box_to_widget_rect(self.crop_box)
        painter.setPen(QPen(QColor("#2f81f7"), 2))
        painter.drawRect(rect)
        painter.fillRect(rect, QColor(47, 129, 247, 35))

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if self.drag_start is None:
            return
        self._emit_box_from_points(self.drag_start, event.position().toPoint())

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if self.drag_start is None:
            return
        self._emit_box_from_points(self.drag_start, event.position().toPoint())
        self.drag_start = None

    def _emit_box_from_points(self, start: QPoint, end: QPoint) -> None:
        start_img = self._widget_point_to_image_point(start)
        end_img = self._widget_point_to_image_point(end)
        left = max(0, min(start_img.x(), end_img.x()))
        top = max(0, min(start_img.y(), end_img.y()))
        right = min(self.source_image.width, max(start_img.x(), end_img.x()))
        bottom = min(self.source_image.height, max(start_img.y(), end_img.y()))
        if right > left and bottom > top:
            self.crop_changed.emit((left, top, right, bottom))

    def _target_rect(self) -> QRect:
        scaled = self._pixmap.size()
        scaled.scale(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        left = (self.width() - scaled.width()) // 2
        top = (self.height() - scaled.height()) // 2
        return QRect(left, top, scaled.width(), scaled.height())

    def _image_box_to_widget_rect(self, box: tuple[int, int, int, int]) -> QRect:
        target = self._target_rect()
        sx = target.width() / self.source_image.width
        sy = target.height() / self.source_image.height
        left, top, right, bottom = box
        return QRect(
            target.left() + int(left * sx),
            target.top() + int(top * sy),
            max(1, int((right - left) * sx)),
            max(1, int((bottom - top) * sy)),
        )

    def _widget_point_to_image_point(self, point: QPoint) -> QPoint:
        target = self._target_rect()
        x = min(max(point.x(), target.left()), target.right()) - target.left()
        y = min(max(point.y(), target.top()), target.bottom()) - target.top()
        image_x = int(x * self.source_image.width / max(1, target.width()))
        image_y = int(y * self.source_image.height / max(1, target.height()))
        return QPoint(image_x, image_y)


class CropAdjustDialog(QDialog):
    def __init__(
        self,
        source_image: Image.Image,
        crop_box: tuple[int, int, int, int],
        parent=None,  # noqa: ANN001
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adjust Crop")
        self.resize(820, 620)
        self.source_image = source_image

        self.preview = CropPreviewWidget(source_image)
        self.preview.crop_changed.connect(self._set_crop_box)

        width, height = source_image.size
        left, top, right, bottom = crop_box
        self.left = self._spin(0, width - 1, left)
        self.top = self._spin(0, height - 1, top)
        self.right = self._spin(1, width, right)
        self.bottom = self._spin(1, height, bottom)
        for spin in (self.left, self.top, self.right, self.bottom):
            spin.valueChanged.connect(self._update_preview)

        form = QFormLayout()
        form.addRow("Left", self.left)
        form.addRow("Top", self.top)
        form.addRow("Right", self.right)
        form.addRow("Bottom", self.bottom)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(apply_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview)
        layout.addLayout(form)
        layout.addLayout(buttons)
        self._update_preview()

    def _spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def crop_box(self) -> tuple[int, int, int, int]:
        left = min(self.left.value(), self.right.value() - 1)
        top = min(self.top.value(), self.bottom.value() - 1)
        right = max(self.right.value(), left + 1)
        bottom = max(self.bottom.value(), top + 1)
        return left, top, right, bottom

    def cropped_image(self) -> Image.Image:
        return self.source_image.crop(self.crop_box())

    def _set_crop_box(self, crop_box: tuple[int, int, int, int]) -> None:
        left, top, right, bottom = crop_box
        self.left.setValue(left)
        self.top.setValue(top)
        self.right.setValue(right)
        self.bottom.setValue(bottom)

    def _update_preview(self) -> None:
        self.preview.set_crop_box(self.crop_box())
