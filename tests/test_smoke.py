"""Smoke test: verifies the package installs and imports correctly."""

import pyrosense_sim


def test_package_imports() -> None:
    assert pyrosense_sim.__version__ == "0.1.0"
