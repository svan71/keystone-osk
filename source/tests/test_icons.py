# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from qt_window_test_helpers import *
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap
from keystone_osk.icons import build_bundled_tray_icon


def _nonnull_icon():
    pm = QPixmap(8, 8)
    pm.fill()
    return QIcon(pm)


def _resolved_with_icons(icons):
    from keystone_osk.theme import THEMES, ResolvedTheme
    return ResolvedTheme(id="custom-kde", source="user", palette=THEMES["dracula"], icons=icons)


def _write_user_theme_pack(tmp_path, theme_id, data):
    pack_dir = tmp_path / "keystone" / "themes" / theme_id
    pack_dir.mkdir(parents=True)
    (pack_dir / "theme.json").write_text(json.dumps({"schema_version": 1, "id": theme_id, **data}), encoding="utf-8")
    return pack_dir


def test_user_theme_tray_icon_path_file_wins(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    pack_dir = _write_user_theme_pack(tmp_path, "custom-kde", {
        "inherits": "dracula",
        "icons": {"tray": "icons/tray.svg"},
    })
    icon_file = pack_dir / "icons" / "tray.svg"
    icon_file.parent.mkdir()
    icon_file.write_text("<svg/>", encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    icon = icons_module.build_tray_icon(
        "custom-kde",
        from_theme=lambda name: pytest.fail(f"icon theme fallback should not run for {name}"),
    )

    assert not icon.isNull()


def test_user_theme_missing_tray_icon_file_falls_through(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    _write_user_theme_pack(tmp_path, "custom-kde", {
        "inherits": "dracula",
        "icons": {"tray": "icons/missing.svg"},
    })
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    icon = icons_module.build_tray_icon(
        "custom-kde",
        from_theme=lambda name: _NamedThemeIcon("keystone-status-symbolic") if name == "keystone-status-symbolic" else QIcon(),
        bundled_path=tmp_path / "nope.svg",
    )

    assert icon.name() == "keystone-status-symbolic"


def test_builtin_theme_without_icon_files_uses_python_symbolic_fallback(app) -> None:
    import keystone_osk.icons as icons_module
    import keystone_osk.theme as theme_module
    calls = []

    assert theme_module.resolve_theme("dracula").icons == {}

    def fake_from_theme(name):
        calls.append(name)
        return _NamedThemeIcon("keystone-status-dracula-symbolic") if name == "keystone-status-dracula-symbolic" else QIcon()

    icon = icons_module.build_tray_icon("dracula", from_theme=fake_from_theme, bundled_path=Path("/nonexistent/nope.svg"))

    assert calls == ["keystone-status-dracula-symbolic"]
    assert icon.name() == "keystone-status-dracula-symbolic"


def test_theme_tray_icon_used_first(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    icon_file = tmp_path / "icons" / "tray.svg"
    icon_file.parent.mkdir(parents=True)
    icon_file.write_text("<svg/>", encoding="utf-8")
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: _resolved_with_icons({"tray": "icons/tray.svg"}))
    monkeypatch.setattr(icons_module, "active_theme_dir", lambda theme: tmp_path)
    icon = icons_module.build_tray_icon("custom-kde", from_theme=lambda name: QIcon())
    assert not icon.isNull()


def test_invalid_theme_icon_path_is_skipped(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: _resolved_with_icons({"tray": "../escape.svg"}))
    monkeypatch.setattr(icons_module, "active_theme_dir", lambda theme: tmp_path)
    # Escapes theme dir -> skipped -> falls through to generated pixmap (never null)
    icon = icons_module.build_tray_icon("custom-kde", from_theme=lambda name: QIcon(), bundled_path=tmp_path / "nope.svg")
    assert not icon.isNull()


def test_missing_theme_icon_file_is_skipped(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: _resolved_with_icons({"tray": "icons/missing.svg"}))
    monkeypatch.setattr(icons_module, "active_theme_dir", lambda theme: tmp_path)
    icon = icons_module.build_tray_icon(
        "custom-kde",
        from_theme=lambda name: _NamedThemeIcon("keystone-status-symbolic") if name == "keystone-status-symbolic" else QIcon(),
        bundled_path=tmp_path / "nope.svg",
    )
    assert icon.name() == "keystone-status-symbolic"


def test_status_symbolic_fallback(app, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: None)
    def fake_from_theme(name):
        return _NamedThemeIcon("keystone-status-symbolic") if name == "keystone-status-symbolic" else QIcon()
    icon = icons_module.build_tray_icon("dracula", from_theme=fake_from_theme, bundled_path=Path("/nonexistent/nope.svg"))
    assert icon.name() == "keystone-status-symbolic"


def test_generated_pixmap_is_last_resort(app, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: None)
    icon = icons_module.build_tray_icon("dracula", from_theme=lambda name: QIcon(), bundled_path=Path("/nonexistent/nope.svg"))
    assert not icon.isNull()  # generated pixmap is never null


def test_generated_tray_icon_body_is_landscape_rectangle() -> None:
    # The tray/app icon should read as a keyboard (clearly wider than tall),
    # not a near-square. Lock a landscape aspect for both desktops.
    for is_kde in (False, True):
        body = tray_icon_keyboard_body_rect(is_kde=is_kde)
        assert body.width() / body.height() >= 1.7


def test_bundled_tray_svg_body_is_landscape_rectangle() -> None:
    import re

    text = BUNDLED_TRAY_ICON_PATH.read_text(encoding="utf-8")
    body_line = next(line for line in text.splitlines() if 'fill="none"' in line)
    width = float(re.search(r'width="([\d.]+)"', body_line).group(1))
    height = float(re.search(r'height="([\d.]+)"', body_line).group(1))
    assert width / height >= 1.7


# ---------------------------------------------------------------------------
# Helpers for pixel-level icon comparison
# ---------------------------------------------------------------------------

def _icon_to_image(icon):
    from PySide6.QtCore import QSize
    return icon.pixmap(QSize(64, 64)).toImage()


def _images_equal(img_a, img_b) -> bool:
    if img_a.size() != img_b.size():
        return False
    for y in range(img_a.height()):
        for x in range(img_a.width()):
            if img_a.pixel(x, y) != img_b.pixel(x, y):
                return False
    return True


def _null_from_theme(name):
    return QIcon()


# ---------------------------------------------------------------------------
# Stub classes for icon theme testing
# ---------------------------------------------------------------------------

class _FallbackThemeIcon:
    """Simulates an icon theme resolving a missing -symbolic name to the launcher icon."""
    def isNull(self): return False
    def name(self): return "keystone"   # resolved/fallback name != requested name


def _fallback_from_theme(name):
    return _FallbackThemeIcon()


class _NamedThemeIcon:
    def __init__(self, n): self._n = n
    def isNull(self): return False
    def name(self): return self._n


# ---------------------------------------------------------------------------
# Regression tests: launcher-icon fallback must be rejected
# ---------------------------------------------------------------------------

def test_themed_fallback_to_launcher_is_rejected_on_kde(app, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: None)

    icon = icons_module.build_tray_icon("mocha", is_kde=True, from_theme=_fallback_from_theme)

    # The stub is NOT a QIcon — proves the loop did not return the fallback stub
    assert isinstance(icon, QIcon)
    expected = build_generated_tray_icon("mocha", is_kde=True)
    assert _images_equal(_icon_to_image(icon), _icon_to_image(expected))


def test_themed_fallback_to_launcher_is_rejected_on_gnome(app, monkeypatch) -> None:
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: None)

    icon = icons_module.build_tray_icon("mocha", is_kde=False, from_theme=_fallback_from_theme)

    assert isinstance(icon, QIcon)
    expected = build_bundled_tray_icon()
    assert _images_equal(_icon_to_image(icon), _icon_to_image(expected))


# ---------------------------------------------------------------------------
# KDE vs GNOME tray icon selection tests
# ---------------------------------------------------------------------------

def test_kde_tray_icon_uses_theme_aware_generated_color(app, monkeypatch) -> None:
    """On KDE, build_tray_icon must return the generated (theme-aware) icon,
    not the bundled SVG.  For mocha the generated color is #cdd6f4."""
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: None)

    icon = icons_module.build_tray_icon("mocha", is_kde=True, from_theme=_null_from_theme)

    expected_generated = build_generated_tray_icon("mocha", is_kde=True)
    expected_bundled = build_bundled_tray_icon()

    result_img = _icon_to_image(icon)
    generated_img = _icon_to_image(expected_generated)
    bundled_img = _icon_to_image(expected_bundled)

    assert _images_equal(result_img, generated_img), (
        "KDE tray icon should equal the generated (theme-aware) icon"
    )
    assert not _images_equal(result_img, bundled_img), (
        "KDE tray icon must NOT equal the bundled SVG icon"
    )


def test_gnome_tray_icon_still_uses_bundled_svg(app, monkeypatch) -> None:
    """On GNOME (is_kde=False), build_tray_icon must still return the bundled SVG."""
    import keystone_osk.icons as icons_module
    monkeypatch.setattr(icons_module, "active_resolved_theme", lambda theme: None)

    icon = icons_module.build_tray_icon("dracula", is_kde=False, from_theme=_null_from_theme)

    expected_bundled = build_bundled_tray_icon()

    result_img = _icon_to_image(icon)
    bundled_img = _icon_to_image(expected_bundled)

    assert _images_equal(result_img, bundled_img), (
        "GNOME tray icon should equal the bundled SVG icon"
    )
