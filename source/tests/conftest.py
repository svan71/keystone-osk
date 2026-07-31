# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest


@pytest.fixture(scope="module")
def app():
    qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    QApplication = qtwidgets.QApplication
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])
