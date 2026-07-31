# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import tomllib
from pathlib import Path


def test_pyproject_declares_keystone_osk_entrypoint() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "keystone-osk"
    assert data["project"]["readme"] == "README.md"
    assert data["project"]["license"] == "GPL-3.0-or-later"
    assert data["project"]["license-files"] == ["LICENSE"]
    assert data["project"]["requires-python"] == ">=3.11"
    assert data["project"]["scripts"]["keystone-osk"] == "keystone_osk.app:main"
    assert "data/*.txt" in data["tool"]["setuptools"]["package-data"]["keystone_osk"]
    assert "data/*.svg" in data["tool"]["setuptools"]["package-data"]["keystone_osk"]
    assert "themes/*/theme.json" in data["tool"]["setuptools"]["package-data"]["keystone_osk"]
