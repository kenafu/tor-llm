from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image


def prepare_image_for_llm(
    image: Image.Image,
    max_long_edge: int,
    image_format: str,
    jpeg_quality: int,
) -> tuple[str, str]:
    prepared = image.convert("RGB")
    width, height = prepared.size
    long_edge = max(width, height)
    if max_long_edge > 0 and long_edge > max_long_edge:
        scale = max_long_edge / long_edge
        prepared = prepared.resize((int(width * scale), int(height * scale)))

    buffer = BytesIO()
    if image_format == "jpeg":
        prepared.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        mime = "image/jpeg"
    else:
        prepared.save(buffer, format="PNG")
        mime = "image/png"
    return mime, base64.b64encode(buffer.getvalue()).decode("ascii")

