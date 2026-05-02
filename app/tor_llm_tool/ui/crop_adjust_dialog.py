from __future__ import annotations

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from tor_llm_tool.ui.image_utils import pil_to_pixmap


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

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(360)
        self.preview.setStyleSheet("QLabel { background: #1f2328; }")

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

    def _update_preview(self) -> None:
        cropped = self.cropped_image()
        pixmap = pil_to_pixmap(cropped)
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
