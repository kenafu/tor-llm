from tor_llm_tool.providers.lmstudio import _extract_stream_delta


def test_extract_stream_delta_chat_completion_chunk():
    line = 'data: {"choices":[{"delta":{"content":"hello"}}]}'

    assert _extract_stream_delta(line) == "hello"


def test_extract_stream_delta_ignores_done():
    assert _extract_stream_delta("data: [DONE]") == ""
