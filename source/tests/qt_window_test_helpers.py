import pytest

# Qt/window tests need PySide6. Skip the whole module cleanly (instead of a hard
# collection error) so the pure suite can be collected without PySide6 installed.
pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from logic_test_helpers import *  # noqa: E402,F401,F403

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication

import keystone_osk.app as keyboard_app
import keystone_osk.doctor as doctor_module
from keystone_osk.autocomplete import AutocompleteEngine
from keystone_osk.backend import YdotoolBackend, ydotool_key_args
from keystone_osk.config import learned_words_path, system_theme_dir, user_theme_dir, window_state_path
from keystone_osk.geometry import PositionedKey, Rect
from keystone_osk.geometry import build_full_key_geometry, build_key_geometry
from keystone_osk.icons import (
    BUNDLED_TRAY_ICON_PATH,
    build_generated_tray_icon,
    build_tray_icon,
    show_top_restore_fallback_if_needed,
    tray_icon_system_fallback_candidates,
    tray_icon_color,
    tray_icon_keyboard_body_rect,
    tray_icon_theme_candidates,
)
from keystone_osk.input_model import is_repeatable_key, key_label_display
from keystone_osk.layout import build_linux_layout
from keystone_osk.platform import (
    is_kde_session,
    keyboard_panel_rect,
    keyboard_window_flags,
    restore_icon_window_flags,
    should_use_manual_resize,
)
from keystone_osk.rendering import COMMON_EMOJIS, KEYBOARD_TITLE, emoji_picker_font
from keystone_osk.state import (
    clamp_restore_icon_geometry,
    default_restore_icon_geometry,
    load_auto_cap_enabled,
    load_full_window_size,
    load_keyboard_mode,
    load_keyboard_theme,
    load_restore_icon_geometry,
    load_suggestions_enabled,
    load_window_position,
    load_window_size,
    save_auto_cap_enabled,
    save_restore_icon_geometry,
    save_suggestions_enabled,
    save_window_position,
)
from keystone_osk.theme import (
    BUILTIN_THEME_IDS,
    THEME_PACK_FORBIDDEN_SECTIONS,
    THEME_PACK_SAFE_SECTIONS,
    bundled_theme_dir,
    default_theme_pack_id,
    key_paint_style,
    load_theme_pack,
    restore_icon_background_color,
    restore_icon_foreground_color,
    theme_pack_path,
    theme_pack_search_dirs,
    theme_palette,
    validate_theme_pack,
)
from keystone_osk.visual import (
    clamp_window_position,
    control_font_size,
    fit_window_size_to_screen,
    key_label_font_size,
    key_label_font_weight,
    key_label_text_rect,
    minimized_keyboard_body_rect,
    minimized_keyboard_key_rects,
    numpad_secondary_font_size,
    shifted_label_style,
    shifted_main_font_size,
    shifted_underscore_line,
    top_right_window_position,
)
from keystone_osk.app import (
    DesktopRestoreIcon,
    FULL_WINDOW_HEIGHT,
    FULL_WINDOW_WIDTH,
    KeyboardWindow,
    MIN_FULL_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    fit_and_position_window,
)
