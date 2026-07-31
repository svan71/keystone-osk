# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

pytest.importorskip("PySide6.QtCore", exc_type=ImportError)

from PySide6.QtCore import QRect

from keystone_osk.visual import accent_strip_geometry


def test_centering_over_key():
    key_rect = QRect(100, 200, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, cell_rects = accent_strip_geometry(
        key_rect, 3, screen, cell=40, gap=4, margin=6
    )
    center_x = strip_rect.center().x()
    key_center_x = key_rect.center().x()
    assert abs(center_x - key_center_x) <= 1


def test_correct_cell_count():
    key_rect = QRect(100, 200, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, cell_rects = accent_strip_geometry(
        key_rect, 5, screen, cell=40, gap=4, margin=6
    )
    assert len(cell_rects) == 5


def test_cells_are_left_to_right():
    key_rect = QRect(100, 200, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, cell_rects = accent_strip_geometry(
        key_rect, 3, screen, cell=40, gap=4, margin=6
    )
    assert cell_rects[0].left() < cell_rects[1].left() < cell_rects[2].left()


def test_cells_inside_strip():
    key_rect = QRect(100, 200, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, cell_rects = accent_strip_geometry(
        key_rect, 3, screen, cell=40, gap=4, margin=6
    )
    for cr in cell_rects:
        assert cr.left() >= strip_rect.left()
        assert cr.right() <= strip_rect.right()
        assert cr.top() >= strip_rect.top()
        assert cr.bottom() <= strip_rect.bottom()


def test_strip_above_key():
    key_rect = QRect(100, 300, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, _ = accent_strip_geometry(
        key_rect, 3, screen, cell=40, gap=4, margin=6
    )
    assert strip_rect.bottom() <= key_rect.top()


def test_flip_below_when_no_room_above():
    key_rect = QRect(100, 0, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, _ = accent_strip_geometry(
        key_rect, 3, screen, cell=40, gap=4, margin=6
    )
    assert strip_rect.top() >= key_rect.bottom()


def test_left_edge_clamping():
    key_rect = QRect(0, 300, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, _ = accent_strip_geometry(
        key_rect, 10, screen, cell=40, gap=4, margin=6
    )
    assert strip_rect.left() >= screen.left()


def test_right_edge_clamping():
    key_rect = QRect(1280, 300, 50, 40)
    screen = QRect(0, 0, 1280, 720)
    strip_rect, _ = accent_strip_geometry(
        key_rect, 10, screen, cell=40, gap=4, margin=6
    )
    assert strip_rect.right() <= screen.right()
