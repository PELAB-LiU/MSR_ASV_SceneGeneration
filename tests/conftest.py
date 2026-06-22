"""Shared pytest fixtures for utils tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """Directory tree with mixed file extensions for file_system_utils tests."""
    root = tmp_path / "data"
    (root / "nested").mkdir(parents=True)
    (root / "a.json").write_text("{}", encoding="utf-8")
    (root / "nested" / "b.json").write_text("{}", encoding="utf-8")
    (root / "c.txt").write_text("hello", encoding="utf-8")
    (root / "nested" / "d.pkl.gz").write_bytes(b"\x1f\x8b\x08")
    return root


@pytest.fixture
def zip_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Single file and nested directory for archive_utils tests."""
    source_dir = tmp_path / "bundle"
    source_dir.mkdir()
    (source_dir / "inner.txt").write_text("nested", encoding="utf-8")
    lone_file = tmp_path / "readme.txt"
    lone_file.write_text("top", encoding="utf-8")
    zip_path = tmp_path / "out.zip"
    return source_dir, lone_file, zip_path
