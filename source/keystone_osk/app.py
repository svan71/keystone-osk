from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QWidget

from keystone_osk.autocomplete import AutocompleteEngine, load_engine
from keystone_osk.autocomplete_ui import AutocompleteUIMixin
from keystone_osk.backend import BackendWorkerQueue, YdotoolBackend
from keystone_osk.constants import APP_ID
from keystone_osk.control import CONTROL_FLAG_COMMANDS, ControlSocketInUseError, KeyboardControlServer, control_socket_path, send_control_command
from keystone_osk.doctor import doctor_report
from keystone_osk.geometry import PositionedKey, build_full_key_geometry, build_key_geometry, hit_test
from keystone_osk.icons import build_tray_icon, show_top_restore_fallback_if_needed
from keystone_osk.input_model import ONE_SHOT_MODIFIERS
from keystone_osk.input_ui import InputUIMixin, log_status
from keystone_osk.menu_ui import MenuUIMixin
from keystone_osk.window_ui import WindowInteractionMixin
from keystone_osk.layout import build_linux_layout
from keystone_osk.platform import (
    detect_color_scheme,
    has_display_environment,
    is_kde_session,
    keyboard_resize_margin,
    keyboard_window_flags,
    preferred_qt_platform,
)
from keystone_osk.rendering import KEYBOARD_TITLE, KeyboardRenderingMixin
from keystone_osk.state import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FULL_WINDOW_HEIGHT,
    FULL_WINDOW_WIDTH,
    MIN_FULL_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    default_window_size,
    load_auto_cap_enabled,
    load_full_window_size,
    load_keyboard_mode,
    load_numpad_output_mode,
    persisted_keyboard_theme,
    load_restore_icon_geometry,
    load_suggestions_enabled,
    load_window_position,
    load_window_size,
    save_full_window_size,
    save_keyboard_mode,
    save_keyboard_theme,
    save_numpad_output_mode,
    save_window_size,
    save_window_state_fields,
)
from keystone_osk.theme import DRACULA_THEME_ID, app_menu_style_sheet, discover_valid_theme_ids, first_run_theme_id, invalidate_theme_cache, resolve_theme, resolve_theme_id, theme_pack_report_lines
from keystone_osk.visual import (
    clamp_window_position,
    fit_window_size_to_screen,
    top_right_window_position,
)
from keystone_osk.widgets import ClipboardBridge, DesktopRestoreIcon, ModifierCancelOverlay, PanelRestoreButton

PREVIEW_WINDOW_WIDTH = 1120
PREVIEW_WINDOW_HEIGHT = 470
COLLAPSED_WINDOW_MIN_WIDTH = 360
COLLAPSED_WINDOW_HEIGHT = 92


class KeyboardWindow(KeyboardRenderingMixin, AutocompleteUIMixin, InputUIMixin, MenuUIMixin, WindowInteractionMixin, QWidget):
    def __init__(
        self,
        startup_size: QSize | None = None,
        persist_window_state: bool = True,
        debug_keys: bool = False,
        autocomplete_engine: AutocompleteEngine | None = None,
        theme: str | None = None,
        enable_control_server: bool = False,
    ) -> None:
        super().__init__()
        self._is_kde = is_kde_session()
        self.layout_spec = build_linux_layout()
        self._clipboard_bridge = ClipboardBridge(self)
        _cb_reader = self._clipboard_bridge.reader()
        _cb_writer = self._clipboard_bridge.writer()
        self.backend = (
            BackendWorkerQueue(
                YdotoolBackend(clipboard_reader=_cb_reader, clipboard_writer=_cb_writer),
                error_handler=lambda exc: log_status(f"ydotool backend worker failed: {exc}"),
            )
            if persist_window_state
            else YdotoolBackend(clipboard_reader=_cb_reader, clipboard_writer=_cb_writer)
        )
        self.autocomplete = autocomplete_engine or load_engine()
        self._persist_autocomplete = autocomplete_engine is None
        self.setWindowTitle(KEYBOARD_TITLE)
        self._persist_window_state = persist_window_state
        self._debug_keys = debug_keys
        self._suggestions_enabled = load_suggestions_enabled() if self._persist_window_state else True
        self._auto_cap_enabled = load_auto_cap_enabled() if self._persist_window_state else True
        self._capitalize_next_letter = True
        self._last_space_was_auto_suggestion = False
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)
            app.aboutToQuit.connect(self._shutdown_backend)
            if self._persist_window_state:
                app.aboutToQuit.connect(self._save_window_state)
        saved_mode = load_keyboard_mode() if self._persist_window_state and startup_size is None else "compact"
        if theme is not None:
            self._theme_name = resolve_theme_id(theme, discover_valid_theme_ids(), strict=False) or DRACULA_THEME_ID
            if self._persist_window_state:
                save_keyboard_theme(self._theme_name)
        else:
            # First launch (nothing persisted): follow the desktop's light/dark
            # preference. Once the user picks a theme it is saved and wins here.
            persisted = persisted_keyboard_theme() if self._persist_window_state else None
            self._theme_name = persisted or first_run_theme_id(detect_color_scheme())
        self.setMinimumSize(MIN_FULL_WINDOW_WIDTH if saved_mode == "full" else MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        compact_size = load_window_size() if self._persist_window_state else default_window_size()
        full_size = load_full_window_size() if self._persist_window_state else QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT)
        startup_size = startup_size or (full_size if saved_mode == "full" else compact_size)
        self.resize(startup_size)
        self.setWindowFlags(keyboard_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self._apply_window_opacity()
        self._drag_offset: QPoint | None = None
        self._system_window_action_active = False
        self._active_resize_edges = None
        self._resize_origin_geometry = QRect()
        self._resize_origin_global = QPoint()
        self._resize_margin = keyboard_resize_margin(self._is_kde)
        self._is_collapsed = False
        self._expanded_size = QSize(startup_size)
        self._keyboard_mode = saved_mode
        self._numpad_output_mode = load_numpad_output_mode() if self._persist_window_state else "reliable"
        if self._numpad_output_mode == "true-keypad":
            self.backend.ensure_numlock_on()
        self._compact_size = QSize(compact_size if saved_mode == "full" else startup_size)
        self._full_size = QSize(startup_size if saved_mode == "full" else full_size)
        self._restore_geometry = QRect()
        self._close_rect = QRectF()
        self._minimize_rect = QRectF()
        self._mode_toggle_rect = QRectF()
        self._menu_rect = QRectF()
        self._title_rect = QRectF()
        self._emoji_picker_visible = False
        self._emoji_rects: tuple[tuple[QRectF, str], ...] = ()
        self._hovered_key_id: str | None = None
        self._pressed_key_id: str | None = None
        self._locked_key_labels: set[str] = set()
        self._modifier_cancel_overlay = ModifierCancelOverlay(self._handle_outside_overlay_click, is_kde=self._is_kde)
        self._emoji_cancel_overlay = ModifierCancelOverlay(self._handle_outside_overlay_click, is_kde=self._is_kde, popup=False)
        self._positioned_keys: tuple[PositionedKey, ...] = ()
        self._suggestion_rects: tuple[tuple[QRectF, str], ...] = ()
        self._current_word = ""
        self._autocomplete_buffer = ""
        self._autocomplete_cursor = 0
        self._suggestions: tuple[str, ...] = ()
        self._pending_key: PositionedKey | None = None
        self._pending_emoji: str | None = None
        self._repeat_key: PositionedKey | None = None
        self._repeat_timer = QTimer(self)
        self._repeat_timer.setSingleShot(True)
        self._repeat_timer.timeout.connect(self._repeat_held_key)
        self._accent_pending_key: PositionedKey | None = None
        self._accent_hold_timer = QTimer(self)
        self._accent_hold_timer.setSingleShot(True)
        self._accent_hold_timer.timeout.connect(self._open_accent_strip)
        self._accent_strip = None
        self._accent_strip_open = False
        self._autocomplete_save_pending = False
        self._autocomplete_save_timer = QTimer(self)
        self._autocomplete_save_timer.setSingleShot(True)
        self._autocomplete_save_timer.setInterval(1500)
        self._autocomplete_save_timer.timeout.connect(self._flush_autocomplete_save)
        self._tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self._panel_button = PanelRestoreButton(self._restore_from_panel, theme=self._theme_name)
        self._desktop_icon = DesktopRestoreIcon(
            self._restore_from_panel,
            close_callback=self._close_desktop_restore_icon,
            persist_geometry=persist_window_state,
            theme=self._theme_name,
        )
        self._app_menu = self._build_app_menu()
        self._snippets_menu = None
        self._tray_menu = self._build_tray_menu()
        self._tray_icon = QSystemTrayIcon(build_tray_icon(self._theme_name), self)
        self._tray_icon.setToolTip(KEYBOARD_TITLE)
        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._handle_tray_activation)
        if self._tray_available:
            self._tray_icon.show()
        self._control_server = (
            KeyboardControlServer(
                self,
                {
                    "show": self._control_show,
                    "hide": self._control_hide,
                    "toggle": self._control_toggle,
                    "quit": self._control_quit,
                    "status": self._control_status,
                    "theme": self._control_theme,
                    "mode": self._control_mode,
                    "numpad": self._control_numpad,
                },
            )
            if enable_control_server
            else None
        )

    def _key_at(self, x: float, y: float) -> PositionedKey | None:
        if self._is_collapsed:
            return None
        if not self._positioned_keys:
            self._positioned_keys = self._keyboard_geometry().keys
        return hit_test(self._positioned_keys, x, y)

    def _keyboard_geometry(self):
        if self._keyboard_mode == "full":
            return build_full_key_geometry(self.width(), self.height(), is_kde=self._is_kde)
        return build_key_geometry(self.layout_spec, self.width(), self.height(), is_kde=self._is_kde)

    def _suggestion_at(self, x: float, y: float) -> str | None:
        for rect, suggestion in self._suggestion_rects:
            if rect.contains(x, y):
                return suggestion
        return None

    def _emoji_at(self, x: float, y: float) -> str | None:
        if not self._emoji_picker_visible:
            return None
        for rect, emoji in self._emoji_rects:
            if rect.contains(x, y):
                return emoji
        return None

    def _toggle_collapsed(self) -> None:
        if self._is_collapsed:
            self._is_collapsed = False
            self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            self.resize(self._expanded_size)
            self.update()
            return
        self._expanded_size = self.size()
        self._is_collapsed = True
        self._pressed_key_id = None
        self._hovered_key_id = None
        self._positioned_keys = ()
        self._dismiss_accent_strip()
        self.setMinimumSize(COLLAPSED_WINDOW_MIN_WIDTH, COLLAPSED_WINDOW_HEIGHT)
        self.resize(max(COLLAPSED_WINDOW_MIN_WIDTH, self.width()), COLLAPSED_WINDOW_HEIGHT)
        self.update()

    def _toggle_keyboard_mode(self) -> None:
        self._set_keyboard_mode("full" if self._keyboard_mode == "compact" else "compact")

    def _set_keyboard_mode(self, mode: str) -> None:
        if mode == self._keyboard_mode:
            self._refresh_mode_action()
            return
        if mode == "full":
            self._compact_size = QSize(self.size())
            if self._persist_window_state:
                save_window_size(self._compact_size)
            self._keyboard_mode = "full"
            if self._persist_window_state:
                save_keyboard_mode("full")
            self.setMinimumSize(MIN_FULL_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            self.resize(self._full_size)
        else:
            self._full_size = QSize(self.size())
            if self._persist_window_state:
                save_full_window_size(self._full_size)
            self._keyboard_mode = "compact"
            if self._persist_window_state:
                save_keyboard_mode("compact")
            self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            self.resize(self._compact_size)
        self.move(clamp_window_position(self.pos(), self.size()))
        self._pressed_key_id = None
        self._hovered_key_id = None
        self._positioned_keys = ()
        self._dismiss_accent_strip()
        self._refresh_mode_action()
        self.update()

    def _toggle_keyboard_theme(self) -> None:
        self._set_keyboard_theme("mocha" if self._theme_name == "dracula" else "dracula")

    def _set_keyboard_theme(self, theme: str) -> None:
        self._theme_name = resolve_theme_id(theme, discover_valid_theme_ids(), strict=False) or DRACULA_THEME_ID
        if self._persist_window_state:
            save_keyboard_theme(self._theme_name)
        invalidate_theme_cache()
        self._apply_keyboard_theme()
        self._apply_window_opacity()
        self.update()

    def _control_show(self, arg: str = "") -> str:
        self.show_keyboard()
        return "OK"

    def _control_hide(self, arg: str = "") -> str:
        self.hide_keyboard()
        return "OK"

    def _control_toggle(self, arg: str = "") -> str:
        self.toggle_keyboard_visibility()
        return "OK"

    def _control_quit(self, arg: str = "") -> str:
        QApplication.instance().quit()
        return "OK"

    def _control_status(self, arg: str = "") -> str:
        app = QApplication.instance()
        qt_platform = app.platformName() if app is not None else "unknown"
        visible = "1" if self.isVisible() else "0"
        geometry = self.geometry()
        return (
            f"OK status qt-platform={qt_platform} input-backend=ydotoold/uinput theme={self._theme_name} "
            f"mode={self._keyboard_mode} visible={visible} "
            f"geometry={geometry.x()},{geometry.y()},{geometry.width()}x{geometry.height()}"
        )

    def _control_mode(self, arg: str) -> str:
        if arg not in ("compact", "full"):
            return "ERR invalid mode"
        try:
            self._set_keyboard_mode(arg)
        except Exception:
            return "ERR mode failed"
        return "OK"

    def _control_numpad(self, arg: str) -> str:
        if arg not in ("reliable", "true-keypad"):
            return "ERR invalid numpad mode"
        try:
            self._set_numpad_output_mode(arg)
        except Exception:
            return "ERR numpad mode failed"
        return "OK"

    def _control_theme(self, arg: str) -> str:
        resolved = resolve_theme_id(arg, discover_valid_theme_ids(), strict=True)
        if resolved is None:
            return "ERR invalid theme"
        try:
            self._set_keyboard_theme(resolved)
        except Exception:
            return "ERR theme failed"
        return "OK"

    def _set_numpad_output_mode(self, mode: str) -> None:
        self._numpad_output_mode = mode
        if self._persist_window_state:
            save_numpad_output_mode(mode)
        if mode == "true-keypad":
            self.backend.ensure_numlock_on()

    def _apply_keyboard_theme(self) -> None:
        self._app_menu.setStyleSheet(app_menu_style_sheet(self._theme_name, border=False))
        self._theme_menu.setStyleSheet(app_menu_style_sheet(self._theme_name, border=False))
        self._tray_menu.setStyleSheet(app_menu_style_sheet(self._theme_name))
        self._tray_icon.setIcon(build_tray_icon(self._theme_name))
        self._panel_button.set_theme(self._theme_name)
        self._desktop_icon.set_theme(self._theme_name)
        self._refresh_theme_action()

    def _apply_window_opacity(self) -> None:
        self.setWindowOpacity(resolve_theme(self._theme_name).opacity)

    def _minimize_to_panel(self) -> None:
        self._restore_geometry = self.geometry()
        self._save_window_state()
        self._pressed_key_id = None
        self._hovered_key_id = None
        self._pending_key = None
        self._dismiss_accent_strip()
        self.hide()
        self._sync_modifier_cancel_overlay()
        self._show_top_restore_fallback_if_needed()
        self._desktop_icon.setGeometry(load_restore_icon_geometry())
        self._desktop_icon.show()
        self._desktop_icon.raise_()

    def _hide_keyboard_keep_top_icon(self) -> None:
        self._restore_geometry = self.geometry()
        self._save_window_state()
        self._stop_key_repeat()
        self._pressed_key_id = None
        self._hovered_key_id = None
        self._pending_key = None
        self.hide()
        self._desktop_icon.hide()
        self._sync_modifier_cancel_overlay()
        self._show_top_restore_fallback_if_needed()

    def _close_desktop_restore_icon(self) -> None:
        self._desktop_icon.hide()
        self._show_top_restore_fallback_if_needed()

    def _show_top_restore_fallback_if_needed(self) -> None:
        show_top_restore_fallback_if_needed(self._panel_button, self._tray_available)

    def _restore_from_panel(self) -> None:
        self._panel_button.hide()
        self._desktop_icon.hide()
        if not self._restore_geometry.isNull():
            # Clamp back onto the current screen: the monitor layout may have
            # changed (unplugged/rearranged) while minimized, which would
            # otherwise restore the window off-screen with no way to recover it.
            size = self._restore_geometry.size()
            clamped = clamp_window_position(self._restore_geometry.topLeft(), size)
            self.setGeometry(QRect(clamped, size))
        self.show()
        self.raise_()
        self._sync_modifier_cancel_overlay()

    def show_keyboard(self) -> None:
        if self.isVisible():
            self.raise_()
            return
        self._restore_from_panel()

    def hide_keyboard(self) -> None:
        if self.isVisible():
            self._hide_keyboard_keep_top_icon()

    def toggle_keyboard_visibility(self) -> None:
        if self.isVisible():
            self.hide_keyboard()
            return
        self.show_keyboard()

    def _sync_modifier_cancel_overlay(self) -> None:
        if not self.isVisible():
            self._modifier_cancel_overlay.hide()
            self._emoji_cancel_overlay.hide()
            return
        if self._app_menu.isVisible() or self._theme_menu.isVisible():
            self._show_menu_cancel_overlay()
            self.raise_()
            self._app_menu.raise_()
            if self._theme_menu.isVisible():
                self._theme_menu.raise_()
            return
        if self._snippets_menu is not None and self._snippets_menu.isVisible():
            self._show_snippets_cancel_overlay()
            return
        if self._emoji_picker_visible:
            self._show_emoji_cancel_overlay()
            return
        self._modifier_cancel_overlay.hide()
        self._emoji_cancel_overlay.hide()

    def _has_cancelable_modifiers(self) -> bool:
        return self._has_one_shot_modifiers() or "Caps" in self._locked_key_labels

    def _clear_cancelable_modifiers(self) -> None:
        self._locked_key_labels.difference_update(ONE_SHOT_MODIFIERS | {"Caps"})
        self._sync_modifier_cancel_overlay()
        self.update()

    def _handle_outside_overlay_click(self) -> None:
        if self._theme_menu.isVisible():
            self._theme_menu.hide()
        if self._app_menu.isVisible():
            self._app_menu.hide()
        if self._snippets_menu is not None and self._snippets_menu.isVisible():
            self._snippets_menu.hide()
        if self._emoji_picker_visible:
            self._emoji_picker_visible = False
            self._emoji_rects = ()
            self.update()
            self._sync_modifier_cancel_overlay()
            return
        if self._accent_strip_open:
            self._dismiss_accent_strip()
            return
        if self._has_cancelable_modifiers():
            self._clear_cancelable_modifiers()
            return
        self._sync_modifier_cancel_overlay()

    def _handle_global_modifier_cancel(self, global_pos: QPoint, buttons, previous_buttons) -> None:
        left_pressed = bool(buttons & Qt.MouseButton.LeftButton)
        left_was_pressed = bool(previous_buttons & Qt.MouseButton.LeftButton)
        if not left_pressed or left_was_pressed or self.frameGeometry().contains(global_pos):
            return
        self._clear_cancelable_modifiers()

    def _clear_pressed_key(self) -> None:
        if self._pressed_key_id is not None or self._hovered_key_id is not None:
            self._pressed_key_id = None
            self._hovered_key_id = None
            self.update()

    def _shutdown_backend(self) -> None:
        # Flush any debounced learned-word save before the event loop stops,
        # otherwise the pending single-shot timer would never fire.
        self._flush_autocomplete_save()
        shutdown = getattr(self.backend, "shutdown", None)
        if callable(shutdown):
            shutdown()

    def _save_window_state(self) -> None:
        if not self._persist_window_state:
            return
        size = self._expanded_size if self._is_collapsed else self.size()
        position = self.pos()
        fields = {
            "x": int(position.x()),
            "y": int(position.y()),
            "mode": "full" if self._keyboard_mode == "full" else "compact",
            "theme": self._theme_name,
            "suggestions_enabled": bool(self._suggestions_enabled),
            "auto_cap_enabled": bool(self._auto_cap_enabled),
        }
        if self._keyboard_mode == "full":
            fields["full"] = {
                "width": max(MIN_FULL_WINDOW_WIDTH, int(size.width())),
                "height": max(MIN_WINDOW_HEIGHT, int(size.height())),
            }
        else:
            fields["width"] = max(MIN_WINDOW_WIDTH, int(size.width()))
            fields["height"] = max(MIN_WINDOW_HEIGHT, int(size.height()))
        save_window_state_fields(fields)


def save_screenshot(path: Path, width: int, height: int, theme: str = "dark", mode: str = "compact") -> None:
    widget = KeyboardWindow(persist_window_state=False, theme=theme)
    if mode == "full":
        widget._keyboard_mode = "full"
        widget.setMinimumSize(MIN_FULL_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    widget.resize(width, height)
    pixmap = QPixmap(widget.size())
    pixmap.fill(Qt.GlobalColor.transparent)
    widget.render(pixmap)
    path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(path))


def fit_and_position_window(window: QWidget, *, restore_saved_position: bool = False) -> None:
    window.resize(fit_window_size_to_screen(window.size()))
    saved_position = load_window_position() if restore_saved_position else None
    if saved_position is not None:
        window.move(clamp_window_position(saved_position, window.size()))
        return
    window.move(top_right_window_position(window.size()))


ALREADY_RUNNING_MESSAGE = (
    "Keystone is already running.\n"
    "Use keystone-osk --show, --hide, --toggle, --quit, --theme, --mode, or --numpad-output."
)


def instance_is_running() -> bool:
    return send_control_command("ping") == "ok pong"


def should_reuse_running_instance(args: argparse.Namespace) -> bool:
    return (
        args.screenshot is None
        and args.width is None
        and args.height is None
        and args.theme is None
        and args.numpad_output is None
        and not args.debug_keys
    )


def running_instance_commands(args: argparse.Namespace, mode_requested: bool) -> list[str]:
    if args.screenshot is not None:
        return []
    commands = []
    if args.theme is not None:
        commands.append(f"theme {args.theme}")
    if mode_requested:
        commands.append(f"mode {args.mode}")
    if args.numpad_output is not None:
        commands.append(f"numpad {args.numpad_output}")
    if commands:
        return commands
    return ["show"] if should_reuse_running_instance(args) else []


def start_only_flag_requested(args: argparse.Namespace) -> bool:
    return args.width is not None or args.height is not None or args.debug_keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--mode", choices=("compact", "full"), default="compact")
    parser.add_argument("--theme")
    parser.add_argument("--numpad-output", choices=("reliable", "true-keypad"))
    parser.add_argument("--debug-keys", action="store_true")
    parser.add_argument("--start-hidden", action="store_true")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--hide", action="store_true")
    parser.add_argument("--toggle", action="store_true")
    parser.add_argument("--quit", action="store_true")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--list-themes", action="store_true")
    raw_args = sys.argv[1:] if argv is None else argv
    mode_requested = any(arg == "--mode" or arg.startswith("--mode=") for arg in raw_args)
    args = parser.parse_args(raw_args)

    control_commands = [command for command in CONTROL_FLAG_COMMANDS if getattr(args, command)]
    if len(control_commands) > 1:
        parser.error("--show, --hide, --toggle, and --quit are mutually exclusive")

    if args.theme is not None:
        valid_ids = discover_valid_theme_ids(os.environ)
        if resolve_theme_id(args.theme, valid_ids, strict=True) is None:
            print(
                f"keystone-osk: invalid theme {args.theme!r}; valid choices: {', '.join(valid_ids)}",
                file=sys.stderr,
            )
            return 2

    if args.doctor:
        print("\n".join(doctor_report()))
        return 0

    if args.status:
        response = send_control_command("status")
        if response and response.startswith("OK status "):
            print(response.removeprefix("OK status "))
            return 0
        print(f"{APP_ID}: no running app", file=sys.stderr)
        return 1

    if args.list_themes:
        print("\n".join(theme_pack_report_lines(os.environ)))
        return 0

    if control_commands:
        command = control_commands[0]
        response = send_control_command(command)
        if response is not None:
            return 0 if response == "OK" else 1
        if command in {"hide", "quit"}:
            return 0
        if not has_display_environment():
            print(f"{APP_ID}: no running app and no display available for --{command}", file=sys.stderr)
            return 1

    # Strict single-instance: start-only flags must not spawn a second keyboard.
    if start_only_flag_requested(args) and args.screenshot is None and instance_is_running():
        print(ALREADY_RUNNING_MESSAGE, file=sys.stderr)
        return 2

    forwarded = running_instance_commands(args, mode_requested)
    for command in forwarded:
        response = send_control_command(command)
        if response is None:
            break  # no instance running -> fall through and start one
        if response != "OK":
            return 1
        if command == "show":
            return 0
    else:
        if forwarded:
            return 0

    # Set the Qt platform plugin just before QApplication reads it, rather than
    # as an import-time side effect (which fired under pytest and any importer).
    os.environ.setdefault("QT_QPA_PLATFORM", preferred_qt_platform())
    app = QApplication(sys.argv[:1])
    if args.screenshot:
        save_screenshot(
            args.screenshot,
            args.width or PREVIEW_WINDOW_WIDTH,
            args.height or PREVIEW_WINDOW_HEIGHT,
            args.theme or "dark",
            args.mode,
        )
        return 0

    explicit_size = args.width is not None or args.height is not None
    startup_size = QSize(args.width or default_window_size().width(), args.height or default_window_size().height()) if explicit_size else None
    try:
        window = KeyboardWindow(startup_size=startup_size, debug_keys=args.debug_keys, theme=args.theme, enable_control_server=True)
    except ControlSocketInUseError:
        print(ALREADY_RUNNING_MESSAGE, file=sys.stderr)
        return 2
    if mode_requested:
        window._set_keyboard_mode(args.mode)
    if args.numpad_output is not None:
        window._set_numpad_output_mode(args.numpad_output)
    # Position before show() so X11 paints in the right place (no flash), then
    # again deferred because Wayland only reports real geometry after mapping.
    # Both calls are deterministic and idempotent, so they agree on the result.
    fit_and_position_window(window, restore_saved_position=not explicit_size)
    if args.start_hidden:
        # Tray-only start: window must never flash. The tray icon is already
        # live from the constructor; keep it that way and leave the keyboard
        # hidden, exactly as a manual Close would.
        window._hide_keyboard_keep_top_icon()
    else:
        window.show()
        QTimer.singleShot(0, lambda: fit_and_position_window(window, restore_saved_position=not explicit_size))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
