# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QMenu, QPushButton, QSystemTrayIcon, QVBoxLayout

import keystone_osk.autostart as autostart
from keystone_osk import __version__
from keystone_osk.constants import APP_NAME
from keystone_osk.input_ui import log_status
from keystone_osk.theme import app_menu_style_sheet, theme_display_label, theme_menu_choices

APP_MENU_GAP = 8
KOFI_URL = "https://ko-fi.com/keystoneosk"
SOURCE_URL = "https://github.com/svan71/keystone-osk"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"


class MenuUIMixin:
    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason not in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            return
        if self.isVisible():
            self.raise_()
            return
        self._restore_from_panel()

    def _build_tray_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(app_menu_style_sheet(self._theme_name))
        self._tray_primary_action = QAction(f"Show {APP_NAME}", self)
        self._tray_primary_action.triggered.connect(self._handle_tray_primary_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(self._tray_primary_action)
        menu.addAction(quit_action)
        menu.aboutToShow.connect(self._refresh_tray_menu_actions)
        self._refresh_tray_menu_actions()
        return menu

    def _build_app_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(app_menu_style_sheet(self._theme_name, border=False))
        minimize_action = QAction("Minimize", self)
        minimize_action.triggered.connect(self._minimize_to_panel)
        close_action = QAction("Close", self)
        close_action.triggered.connect(self._hide_keyboard_keep_top_icon)
        self._mode_action = QAction("", self)
        self._mode_action.triggered.connect(self._toggle_keyboard_mode)
        self._theme_action_group = QActionGroup(self)
        self._theme_action_group.setExclusive(True)
        self._theme_menu = QMenu("Themes", self)
        self._theme_menu.setStyleSheet(app_menu_style_sheet(self._theme_name, border=False))
        self._theme_actions = {}
        for theme_id, label in theme_menu_choices(os.environ):
            action = QAction(label, self)
            action.setCheckable(True)
            # checked=False absorbs the bool QAction.triggered emits; selected_theme
            # binds the loop value. A bare partial() would forward the bool as an arg.
            action.triggered.connect(lambda checked=False, selected_theme=theme_id: self._set_keyboard_theme(selected_theme))
            self._theme_action_group.addAction(action)
            self._theme_menu.addAction(action)
            self._theme_actions[theme_id] = action
        self._suggestions_action = QAction("", self)
        self._suggestions_action.triggered.connect(self._toggle_suggestions_enabled)
        self._learning_action = QAction("", self)
        self._learning_action.triggered.connect(self._toggle_learning_enabled)
        self._auto_cap_action = QAction("", self)
        self._auto_cap_action.triggered.connect(self._toggle_auto_cap_enabled)
        self._autostart_action = QAction("Load on startup", self)
        self._autostart_action.setCheckable(True)
        self._autostart_action.triggered.connect(self._toggle_autostart)
        emoji_action = QAction("Emojis", self)
        emoji_action.triggered.connect(self._toggle_emoji_picker)
        clear_words_action = QAction("Clear Learned Words", self)
        clear_words_action.triggered.connect(self._clear_learned_words)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        about_action = QAction("About Keystone…", self)
        about_action.triggered.connect(self._show_about_dialog)
        menu.addAction(self._mode_action)
        menu.addMenu(self._theme_menu)
        menu.addSeparator()
        menu.addAction(self._suggestions_action)
        menu.addAction(self._learning_action)
        menu.addAction(self._auto_cap_action)
        menu.addAction(self._autostart_action)
        menu.addAction(emoji_action)
        menu.addSeparator()
        menu.addAction(clear_words_action)
        support_action = QAction("Support Keystone ☕", self)
        support_action.triggered.connect(self._open_support_page)
        menu.addSeparator()
        menu.addAction(minimize_action)
        menu.addAction(close_action)
        menu.addAction(quit_action)
        menu.addSeparator()
        menu.addAction(support_action)
        menu.addAction(about_action)
        menu.aboutToShow.connect(self._refresh_autostart_action)
        menu.aboutToHide.connect(self._sync_modifier_cancel_overlay)
        self._refresh_mode_action()
        self._refresh_theme_action()
        self._refresh_suggestions_action()
        self._refresh_learning_action()
        self._refresh_auto_cap_action()
        self._refresh_autostart_action()
        return menu

    def _show_app_menu(self) -> None:
        menu_size = self._app_menu.sizeHint()
        anchor = self._app_menu_anchor(menu_size)
        self._modifier_cancel_overlay.hide()
        self._app_menu.popup(anchor)
        self._app_menu.raise_()
        QTimer.singleShot(0, self._show_menu_cancel_overlay)

    def _show_menu_cancel_overlay(self) -> None:
        if not self._app_menu.isVisible():
            return
        menu_rect = QRect(self._app_menu.pos(), self._app_menu.sizeHint())
        theme_menu_size = self._theme_menu.sizeHint()
        menu_rect = menu_rect.united(QRect(menu_rect.right() + 1, menu_rect.top(), theme_menu_size.width(), max(menu_rect.height(), theme_menu_size.height())))
        self._modifier_cancel_overlay.show_around_rect(menu_rect)
        self.raise_()
        self._app_menu.raise_()
        if self._theme_menu.isVisible():
            self._theme_menu.raise_()

    def _app_menu_anchor(self, menu_size: QSize) -> QPoint:
        local_x = int(self._menu_rect.center().x() - (menu_size.width() / 2))
        screen = self.screen() or QApplication.primaryScreen()

        def clamped_anchor(local_y: int) -> QPoint:
            anchor = self.mapToGlobal(QPoint(local_x, local_y))
            if screen is None:
                return anchor
            available = screen.availableGeometry()
            max_x = max(available.left(), available.right() - menu_size.width() + 1)
            anchor.setX(min(max(anchor.x(), available.left()), max_x))
            return anchor

        above_y = int(self._menu_rect.top()) - menu_size.height() - APP_MENU_GAP
        above_anchor = clamped_anchor(above_y)
        if screen is not None and above_anchor.y() >= screen.availableGeometry().top():
            return above_anchor
        return clamped_anchor(int(self._menu_rect.bottom()) + APP_MENU_GAP)

    def _refresh_tray_menu_actions(self) -> None:
        self._tray_primary_action.setText("Hide" if self.isVisible() else f"Show {APP_NAME}")

    def _handle_tray_primary_action(self) -> None:
        if self.isVisible():
            self._hide_keyboard_keep_top_icon()
            self._refresh_tray_menu_actions()
            return
        self._restore_from_panel()
        self._refresh_tray_menu_actions()

    def _build_snippets_menu(self) -> "QMenu":
        from keystone_osk.snippets import load_snippets_with_errors
        from keystone_osk.config import snippets_path

        menu = QMenu(self)
        menu.setStyleSheet(app_menu_style_sheet(self._theme_name, border=False))
        snippets, entry_errors, file_error = load_snippets_with_errors()

        path = snippets_path()
        file_exists = path.exists()

        if file_exists and file_error is not None:
            # Whole-file failure (bad JSON, wrong shape, unreadable)
            warn = menu.addAction("⚠ snippets.json has an error — Edit…")
            warn.triggered.connect(lambda _checked=False: self._open_snippets_file())
        elif entry_errors:
            # Per-entry failures alongside some valid snippets (or all failed)
            count = len(entry_errors)
            label = f"⚠ {count} snippet{'s' if count != 1 else ''} couldn't load — Edit…"
            warn = menu.addAction(label)
            warn.triggered.connect(lambda _checked=False: self._open_snippets_file())
            for snippet in snippets:
                action = menu.addAction(snippet.label)
                action.triggered.connect(lambda _checked=False, s=snippet: self._emit_snippet(s))
            menu.addSeparator()
            edit = menu.addAction("Edit snippets…")
            edit.triggered.connect(lambda _checked=False: self._open_snippets_file())
        elif not snippets:
            hint = menu.addAction("No snippets yet — click to create & edit…")
            hint.triggered.connect(lambda _checked=False: self._open_snippets_file())
        else:
            for snippet in snippets:
                action = menu.addAction(snippet.label)
                action.triggered.connect(lambda _checked=False, s=snippet: self._emit_snippet(s))
            menu.addSeparator()
            edit = menu.addAction("Edit snippets…")
            edit.triggered.connect(lambda _checked=False: self._open_snippets_file())

        menu.addSeparator()
        restore = menu.addAction("Restore example snippets…")
        restore.triggered.connect(lambda _checked=False: self._reset_snippets())
        return menu

    def _snippets_entry_errors(self, entry_errors: "list[str]") -> bool:
        """Return True if there are any per-entry errors."""
        return bool(entry_errors)

    def _reset_snippets(self) -> None:
        from keystone_osk.snippets import reset_snippets_file

        reset_snippets_file()
        self._open_snippets_file()

    def _show_snippets_menu(self) -> None:
        menu = self._build_snippets_menu()
        self._snippets_menu = menu
        # Same click-catcher overlay the app menu uses: a native QMenu does not
        # reliably dismiss on outside clicks in this frameless always-on-top OSK
        # window on GNOME/XCB, so cover the desktop around the menu and treat any
        # click there (including on the keyboard) as a dismiss.
        menu.aboutToHide.connect(self._on_snippets_menu_hidden)
        self._modifier_cancel_overlay.hide()
        menu.popup(self.mapToGlobal(self.rect().center()))
        menu.raise_()
        QTimer.singleShot(0, self._show_snippets_cancel_overlay)

    def _show_snippets_cancel_overlay(self) -> None:
        menu = self._snippets_menu
        if menu is None or not menu.isVisible():
            return
        menu_rect = QRect(menu.pos(), menu.sizeHint())
        self._modifier_cancel_overlay.show_around_rect(menu_rect)
        self.raise_()
        menu.raise_()

    def _show_emoji_cancel_overlay(self) -> None:
        if not self._emoji_picker_visible:
            return
        self._emoji_cancel_overlay.show_around_rect(self.frameGeometry())
        self.raise_()

    def _on_snippets_menu_hidden(self) -> None:
        # Clear the ref FIRST so the sync below sees no open snippets menu and
        # tears the overlay down (no re-show race during aboutToHide).
        self._snippets_menu = None
        self._sync_modifier_cancel_overlay()

    def _emit_snippet(self, snippet) -> None:
        from keystone_osk.snippets import snippet_text

        text = snippet_text(snippet)
        if text:
            self.backend.type_text(text)

    def _open_snippets_file(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from keystone_osk.snippets import ensure_snippets_file

        path = ensure_snippets_file()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_support_page(self) -> None:
        self._open_url(KOFI_URL)

    def _open_source_page(self) -> None:
        self._open_url(SOURCE_URL)

    def _open_license_page(self) -> None:
        self._open_url(LICENSE_URL)

    def _open_url(self, url: str) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(url))

    def _build_about_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("About Keystone")
        dialog.setModal(False)
        dialog.setMinimumWidth(360)

        layout = QVBoxLayout(dialog)
        title = QLabel(APP_NAME, dialog)
        title.setObjectName("about-title")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        body = QLabel(
            f"Version {__version__}\n\n"
            "A practical on-screen keyboard for Linux desktops.\n\n"
            "GPL-3.0-or-later\n"
            "Free and source-available. Donations help development.",
            dialog,
        )
        body.setWordWrap(True)

        buttons = QHBoxLayout()
        support_button = QPushButton("Support Keystone", dialog)
        source_button = QPushButton("Source Code", dialog)
        license_button = QPushButton("License", dialog)
        close_button = QPushButton("Close", dialog)
        support_button.clicked.connect(self._open_support_page)
        source_button.clicked.connect(self._open_source_page)
        license_button.clicked.connect(self._open_license_page)
        close_button.clicked.connect(dialog.close)
        for button in (support_button, source_button, license_button, close_button):
            buttons.addWidget(button)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addLayout(buttons)
        return dialog

    def _show_about_dialog(self) -> None:
        dialog = self._build_about_dialog()
        dialog.show()

    def _refresh_mode_action(self) -> None:
        self._mode_action.setText("Compact Keyboard" if self._keyboard_mode == "full" else "Full Keyboard")

    def _refresh_theme_action(self) -> None:
        self._theme_menu.setTitle(f"Themes ({theme_display_label(self._theme_name, os.environ)})")
        for theme_id, action in self._theme_actions.items():
            action.setChecked(theme_id == self._theme_name)
            action.setText(("✓ " if theme_id == self._theme_name else "") + theme_display_label(theme_id, os.environ))

    def _refresh_autostart_action(self) -> None:
        self._autostart_action.setChecked(autostart.is_enabled(os.environ))

    def _toggle_autostart(self) -> None:
        currently_enabled = autostart.is_enabled(os.environ)
        try:
            if currently_enabled:
                autostart.disable(os.environ)
            else:
                autostart.enable(os.environ)
        except OSError as exc:
            # Revert the checkbox to reflect the unchanged on-disk state.
            self._autostart_action.setChecked(currently_enabled)
            log_status(f"keystone-osk: autostart toggle failed: {exc}")
