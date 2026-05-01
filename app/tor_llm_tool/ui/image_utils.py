from __future__ import annotations

from io import BytesIO

from PIL import Image
from PySide6.QtGui import QPixmap


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap

