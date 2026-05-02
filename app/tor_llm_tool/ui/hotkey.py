from __future__ import annotations

import ctypes
import platform
import threading
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal


class GlobalHotkey(QObject):
    activated = Signal()
    failed = Signal(str)

    def __init__(self, hotkey: str) -> None:
        super().__init__()
        self.hotkey = hotkey
        self._thread: threading.Thread | None = None
        self._hotkey_id = 0x544C4C4D
        self._thread_id = 0

    def start(self) -> None:
        if platform.system().lower() != "windows":
            self.failed.emit("Global hotkey is only implemented on Windows.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_windows_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if platform.system().lower() != "windows":
            return
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._thread = None
        self._thread_id = 0

    def restart(self, hotkey: str) -> None:
        self.stop()
        self.hotkey = hotkey
        self.start()

    def _run_windows_loop(self) -> None:
        modifiers, vk = _parse_windows_hotkey(self.hotkey)
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, self._hotkey_id, modifiers, vk):
            self.failed.emit(f"Failed to register global hotkey: {self.hotkey}")
            return

        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312 and msg.wParam == self._hotkey_id:  # WM_HOTKEY
                    self.activated.emit()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, self._hotkey_id)


def _parse_windows_hotkey(hotkey: str) -> tuple[int, int]:
    modifier_map = {
        "ctrl": 0x0002,
        "control": 0x0002,
        "alt": 0x0001,
        "shift": 0x0004,
        "win": 0x0008,
        "meta": 0x0008,
    }
    key_map = {
        "space": 0x20,
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
    }
    for i in range(1, 13):
        key_map[f"f{i}"] = 0x70 + i - 1

    modifiers = 0
    key = ""
    for part in (item.strip().lower() for item in hotkey.split("+")):
        if part in modifier_map:
            modifiers |= modifier_map[part]
        elif part:
            key = part

    if not key:
        key = "space"
    if key in key_map:
        return modifiers, key_map[key]
    if len(key) == 1:
        return modifiers, ord(key.upper())
    return modifiers, 0x20
