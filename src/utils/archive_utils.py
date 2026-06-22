"""Zip archive helpers (no Streamlit dependency)."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Iterable, Union

PathLike = Union[str, Path]


def create_zip_from_directory(source_dir: Path, zip_path: Path) -> Path:
    return create_zip_archive([source_dir], zip_path)


def create_zip_archive(sources: Iterable[PathLike], zip_path: PathLike) -> Path:
    """Pack one or more files or directories into a zip archive."""
    destination = Path(zip_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            path = Path(source)
            if not path.exists():
                continue
            if path.is_file():
                archive.write(path, path.name)
                continue
            for file_path in sorted(path.rglob("*")):
                if file_path.is_file():
                    archive.write(
                        file_path,
                        Path(path.name) / file_path.relative_to(path),
                    )
    return destination
