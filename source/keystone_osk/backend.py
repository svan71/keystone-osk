# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import queue
import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path

from keystone_osk.geometry import PositionedKey


Runner = Callable[[Sequence[str], bool], object]
ErrorHandler = Callable[[Exception], None]
ClipboardReader = Callable[[], "str | None"]
ClipboardWriter = Callable[[str], bool]


MODIFIED_DELETE_KEY_DELAY_MS = 40

# A wedged ydotoold otherwise blocks the worker thread forever and keypresses
# pile up silently in the queue.
BACKEND_CALL_TIMEOUT_S = 5.0

# How long the pasted text must stay on the clipboard before the previous
# clipboard content is restored. The target app reads the clipboard when it
# processes the Ctrl+V keystroke, which happens after ydotool returns.
CLIPBOARD_RESTORE_DELAY_S = 0.35

# The focused app must process the new Wayland clipboard offer before the
# Ctrl+V keystroke arrives, or the paste is silently empty. Live on GNOME:
# ~60-90ms always fails; 150ms is intermittent in real use (the target app is
# busy with popup-close/focus events right after a picker tap, even though
# idle-app probes pass at 120ms); 250ms is reliable. Do not lower again.
CLIPBOARD_SETTLE_DELAY_S = 0.25


KEYCODES = {
    "`": 41,
    "Esc": 1,
    "1": 2,
    "2": 3,
    "3": 4,
    "4": 5,
    "5": 6,
    "6": 7,
    "7": 8,
    "8": 9,
    "9": 10,
    "0": 11,
    "-": 12,
    "=": 13,
    "Backspace": 14,
    "Tab": 15,
    "q": 16,
    "w": 17,
    "e": 18,
    "r": 19,
    "t": 20,
    "y": 21,
    "u": 22,
    "i": 23,
    "o": 24,
    "p": 25,
    "[": 26,
    "]": 27,
    "Enter": 28,
    "Ctrl": 29,
    "a": 30,
    "s": 31,
    "d": 32,
    "f": 33,
    "g": 34,
    "h": 35,
    "j": 36,
    "k": 37,
    "l": 38,
    ";": 39,
    "'": 40,
    "Shift": 42,
    "\\": 43,
    "z": 44,
    "x": 45,
    "c": 46,
    "v": 47,
    "b": 48,
    "n": 49,
    "m": 50,
    ",": 51,
    ".": 52,
    "/": 53,
    "Alt": 56,
    "Space": 57,
    "Caps": 58,
    "F1": 59,
    "F2": 60,
    "F3": 61,
    "F4": 62,
    "F5": 63,
    "F6": 64,
    "F7": 65,
    "F8": 66,
    "F9": 67,
    "F10": 68,
    "Num": 69,
    "NumLock": 69,
    "KP7": 71,
    "KP8": 72,
    "KP9": 73,
    "KPMinus": 74,
    "KP4": 75,
    "KP5": 76,
    "KP6": 77,
    "KPPlus": 78,
    "KP1": 79,
    "KP2": 80,
    "KP3": 81,
    "KP0": 82,
    "KPDot": 83,
    "ScrLk": 70,
    "F11": 87,
    "F12": 88,
    "KPEnter": 96,
    "KPSlash": 98,
    "PrtSc": 99,
    "AltGr": 100,
    "Home": 102,
    "Up": 103,
    "PgUp": 104,
    "Left": 105,
    "Right": 106,
    "End": 107,
    "Down": 108,
    "PgDn": 109,
    "Insert": 110,
    "Delete": 111,
    "Pause": 119,
    "Super": 125,
    "Menu": 127,
    "KPStar": 55,
    "*": 55,
    "+": 78,
}


def keycode_for(label: str) -> int:
    try:
        return KEYCODES[label]
    except KeyError as exc:
        raise ValueError(f"No ydotool keycode mapped for {label!r}") from exc


def ydotool_key_args(label: str, modifiers: Sequence[str] = ()) -> list[str]:
    args = ["ydotool", "key"]
    if label == "Delete" and modifiers:
        args.extend(("--key-delay", str(MODIFIED_DELETE_KEY_DELAY_MS)))
    for modifier in modifiers:
        args.append(f"{keycode_for(modifier)}:1")
    code = keycode_for(label)
    args.extend((f"{code}:1", f"{code}:0"))
    for modifier in reversed(modifiers):
        args.append(f"{keycode_for(modifier)}:0")
    return args


def numlock_is_on(led_root: str = "/sys/class/leds") -> bool | None:
    readable = False
    try:
        brightness_paths = sorted(Path(led_root).glob("*numlock*/brightness"))
    except OSError:
        return None
    for brightness_path in brightness_paths:
        try:
            value = brightness_path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        readable = True
        if value == "1":
            return True
    return False if readable else None


class YdotoolBackend:
    def __init__(
        self,
        runner: Runner | None = None,
        clipboard_reader: ClipboardReader | None = None,
        clipboard_writer: ClipboardWriter | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._runner = runner or partial(subprocess.run, timeout=BACKEND_CALL_TIMEOUT_S)
        self._clipboard_reader = clipboard_reader
        self._clipboard_writer = clipboard_writer
        self._sleep = sleeper or time.sleep

    def press_key(self, key: PositionedKey) -> None:
        self._runner(ydotool_key_args(key.label), check=True)

    def press_key_with_modifiers(self, key: PositionedKey, modifiers: Sequence[str]) -> None:
        self._runner(ydotool_key_args(key.label, modifiers=modifiers), check=True)

    def type_text(self, text: str) -> None:
        if text.isascii():
            self._runner(["ydotool", "type", "-d", "0", "-e", "0", text], check=True)
            return
        previous = self._clipboard_reader() if self._clipboard_reader is not None else None
        writer_ok = self._clipboard_writer is not None and self._clipboard_writer(text)
        if not writer_ok:
            self._runner(["ydotool", "type", "-d", "0", "-e", "0", text], check=True)
            return
        # Wait for the focused app to process the new clipboard offer before
        # sending Ctrl+V; without this, the paste arrives before the Wayland
        # clipboard handshake completes and is silently empty (~60ms races,
        # live-verified on GNOME).
        self._sleep(CLIPBOARD_SETTLE_DELAY_S)
        try:
            self._runner(ydotool_key_args("v", modifiers=("Ctrl",)), check=True)
        finally:
            self._restore_clipboard(previous)

    def _restore_clipboard(self, previous: str | None) -> None:
        # Runs on the worker thread, so queued backend actions wait until the
        # restore lands — a follow-up type_text cannot race the old content.
        if previous is None:
            return
        if self._clipboard_writer is None:
            return
        self._sleep(CLIPBOARD_RESTORE_DELAY_S)
        self._clipboard_writer(previous)

    def type_unicode_text(self, text: str) -> None:
        for char in text:
            self._runner(ydotool_key_args("u", modifiers=("Ctrl", "Shift")), check=True)
            for digit in f"{ord(char):x}":
                self._runner(ydotool_key_args(digit), check=True)
            self._runner(ydotool_key_args("Enter"), check=True)

    def ensure_numlock_on(self) -> None:
        if numlock_is_on() is not False:
            return
        try:
            self._runner(ydotool_key_args("NumLock"), check=True)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass


_STOP = object()


class BackendWorkerQueue:
    def __init__(self, backend: object | None = None, error_handler: ErrorHandler | None = None) -> None:
        self._backend = backend or YdotoolBackend()
        self._error_handler = error_handler
        self._tasks: queue.Queue[tuple[str, tuple[object, ...]] | object] = queue.Queue()
        self._lock = threading.Lock()
        self._closed = False
        self._worker = threading.Thread(target=self._run, name="keystone-backend-worker", daemon=True)
        self._worker.start()

    def press_key(self, key: PositionedKey) -> None:
        self._enqueue("press_key", key)

    def press_key_with_modifiers(self, key: PositionedKey, modifiers: Sequence[str]) -> None:
        self._enqueue("press_key_with_modifiers", key, tuple(modifiers))

    def type_text(self, text: str) -> None:
        self._enqueue("type_text", text)

    def type_unicode_text(self, text: str) -> None:
        self._enqueue("type_unicode_text", text)

    def ensure_numlock_on(self) -> None:
        self._enqueue("ensure_numlock_on")

    def wait_idle(self) -> None:
        self._tasks.join()

    def shutdown(self, timeout: float = 1.0) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._tasks.put(_STOP)
        self._worker.join(timeout)

    def _enqueue(self, method: str, *args: object) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("backend worker is shut down")
            self._tasks.put((method, args))

    def _run(self) -> None:
        while True:
            task = self._tasks.get()
            try:
                if task is _STOP:
                    return
                method, args = task
                getattr(self._backend, method)(*args)
            except Exception as exc:
                self._report_error(exc)
            finally:
                self._tasks.task_done()

    def _report_error(self, exc: Exception) -> None:
        if self._error_handler is None:
            return
        try:
            self._error_handler(exc)
        except Exception:
            pass
