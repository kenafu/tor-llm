from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from tor_llm_tool.settings import AppConfig


def preprocess_for_ocr(image: Image.Image, config: AppConfig) -> Image.Image:
    if not config.ocr.preprocess_image:
        return image

    prepared = image
    if config.ocr.preprocess_grayscale:
        prepared = ImageOps.grayscale(prepared)
    if config.ocr.preprocess_contrast:
        prepared = ImageEnhance.Contrast(prepared).enhance(1.6)
    if config.ocr.preprocess_sharpen:
        prepared = prepared.filter(ImageFilter.SHARPEN)
    return prepared
