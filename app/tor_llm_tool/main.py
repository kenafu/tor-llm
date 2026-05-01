from __future__ import annotations

from tor_llm_tool.settings import load_config
from tor_llm_tool.ui.main_window import run_app


def main() -> int:
    config = load_config()
    return run_app(config)

