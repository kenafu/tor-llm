from tor_llm_tool.providers.lmstudio import _extract_stream_delta
from tor_llm_tool.ui.hotkey import _parse_windows_hotkey


def test_extract_stream_delta_chat_completion_chunk():
    line = 'data: {"choices":[{"delta":{"content":"hello"}}]}'

    assert _extract_stream_delta(line) == "hello"


def test_extract_stream_delta_ignores_done():
    assert _extract_stream_delta("data: [DONE]") == ""


def test_parse_windows_hotkey():
    assert _parse_windows_hotkey("Ctrl+Shift+Space") == (0x0002 | 0x0004, 0x20)
