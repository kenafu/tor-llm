from tor_llm_tool.context import extract_url_candidates


def test_extract_url_candidates():
    urls = extract_url_candidates("See https://example.com/path?q=1 and http://localhost:1234.")

    assert urls == ["https://example.com/path?q=1", "http://localhost:1234"]

