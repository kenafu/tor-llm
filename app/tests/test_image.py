from PIL import Image

from tor_llm_tool.assistant.image import estimate_prepared_image


def test_estimate_prepared_image_resizes_long_edge():
    image = Image.new("RGB", (400, 200), "white")

    mime, size_bytes, dimensions = estimate_prepared_image(image, 100, "jpeg", 80)

    assert mime == "image/jpeg"
    assert size_bytes > 0
    assert dimensions == (100, 50)
