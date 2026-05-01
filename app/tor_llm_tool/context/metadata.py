from __future__ import annotations

import re
from pathlib import Path

from tor_llm_tool.models import CaptureContext


URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)


def extract_url_candidates(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:)]}")
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def collect_context() -> CaptureContext:
    if _is_windows():
        return _collect_windows_context()
    return CaptureContext()


def collect_context_at(x: int, y: int) -> CaptureContext:
    if _is_windows():
        return _collect_windows_context_at(x, y)
    return CaptureContext()


def _is_windows() -> bool:
    import platform

    return platform.system().lower() == "windows"


def _collect_windows_context() -> CaptureContext:
    try:
        import win32gui
    except ImportError:
        return CaptureContext()

    try:
        hwnd = win32gui.GetForegroundWindow()
        return _context_from_hwnd(hwnd)
    except Exception:  # noqa: BLE001
        return CaptureContext()


def _collect_windows_context_at(x: int, y: int) -> CaptureContext:
    try:
        import win32gui
    except ImportError:
        return CaptureContext()

    try:
        hwnd = win32gui.WindowFromPoint((x, y))
        root = win32gui.GetAncestor(hwnd, 2) or hwnd
        return _context_from_hwnd(root)
    except Exception:  # noqa: BLE001
        return CaptureContext()


def _context_from_hwnd(hwnd: int) -> CaptureContext:
    import psutil
    import win32gui
    import win32process

    window_title = win32gui.GetWindowText(hwnd) or ""
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(pid)
    process_name = process.name() or ""
    exe = process.exe()
    app_name = Path(exe).stem if exe else process_name
    return CaptureContext(
        app_name=app_name,
        process_name=process_name,
        window_title=window_title,
    )
