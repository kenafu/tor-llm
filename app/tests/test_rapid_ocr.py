from PIL import Image, ImageDraw

from tor_llm_tool.ocr.rapid import RapidOcrEngine


def test_rapid_ocr_smoke():
    image = Image.new("RGB", (520, 160), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 60), "Hello OCR 123", fill="black")

    result = RapidOcrEngine().recognize(image)

    assert "Hello" in result.text
    assert "OCR" in result.text
