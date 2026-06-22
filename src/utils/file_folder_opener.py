"""
File and folder selection interface so that DataParsers (and callers) can switch
between tkinter-based dialogs (e.g. Windows) and Linux-compatible implementations
(e.g. zenity) by changing only which opener is instantiated.
"""

import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

_ZENITY_NOT_FOUND = (
    "zenity not found. Zenity is a Linux tool and is not available on Windows. "
    "Use TkinterFileOpener() on Windows, or get_default_file_opener() for automatic choice."
)

# Type for file type filters: (description, pattern) e.g. ("zip files", "*.zip")
FileTypes = List[Tuple[str, str]]


class FileFolderOpener(ABC):
    """Interface for opening file/dir dialogs. Implement for tkinter, zenity, etc."""

    @abstractmethod
    def ask_open_dirs(self, initialdir: str = ".") -> List[str]:
        """Ask user to select one or more directories. Returns empty list if cancelled."""
        ...

    @abstractmethod
    def ask_open_files(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> List[str]:
        """Ask user to select one or more files. Returns empty list if cancelled."""
        ...

    @abstractmethod
    def ask_save_file(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> Optional[str]:
        """Ask user for a save path. Returns None if cancelled."""
        ...


class TkinterFileOpener(FileFolderOpener):
    """Uses tkfilebrowser (tkinter). Works well on Windows; may have issues on headless/Wayland Linux."""

    def ask_open_dirs(self, initialdir: str = ".") -> List[str]:
        import tkfilebrowser  # type: ignore[import-untyped]

        result = tkfilebrowser.askopendirnames(initialdir=initialdir)
        return list(result) if result else []

    def ask_open_files(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> List[str]:
        import tkfilebrowser  # type: ignore[import-untyped]

        kwargs: Dict[str, Any] = {"initialdir": initialdir}
        if filetypes is not None:
            kwargs["filetypes"] = filetypes
        result = tkfilebrowser.askopenfilenames(**kwargs)
        return list(result) if result else []

    def ask_save_file(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> Optional[str]:
        import tkfilebrowser  # type: ignore[import-untyped]

        kwargs: Dict[str, Any] = {"initialdir": initialdir}
        if filetypes is not None:
            kwargs["filetypes"] = filetypes
        return tkfilebrowser.asksaveasfilename(**kwargs) or None


class ZenityFileOpener(FileFolderOpener):
    """Uses zenity (common on GNOME/Linux). Good for Linux when tkinter is not suitable."""

    def ask_open_dirs(self, initialdir: str = ".") -> List[str]:
        import subprocess

        try:
            out = subprocess.run(
                [
                    "zenity",
                    "--file-selection",
                    "--directory",
                    "--multiple",
                    "--separator=\n",
                ],
                capture_output=True,
                text=True,
                cwd=initialdir,
            )
            if out.returncode != 0 or not out.stdout.strip():
                return []
            return [p.strip() for p in out.stdout.strip().split("\n") if p.strip()]
        except FileNotFoundError:
            raise RuntimeError(_ZENITY_NOT_FOUND) from None

    def ask_open_files(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> List[str]:
        import subprocess

        args = ["zenity", "--file-selection", "--multiple", "--separator=\n"]
        if filetypes:
            # zenity: --file-filter='Name | pattern1 pattern2'
            for desc, pattern in filetypes:
                args.append(f"--file-filter={desc} | {pattern}")
        try:
            out = subprocess.run(args, capture_output=True, text=True, cwd=initialdir)
            if out.returncode != 0 or not out.stdout.strip():
                return []
            return [p.strip() for p in out.stdout.strip().split("\n") if p.strip()]
        except FileNotFoundError:
            raise RuntimeError(_ZENITY_NOT_FOUND) from None

    def ask_save_file(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> Optional[str]:
        import subprocess

        args = ["zenity", "--file-selection", "--save"]
        if filetypes:
            for desc, pattern in filetypes:
                args.append(f"--file-filter={desc} | {pattern}")
        try:
            out = subprocess.run(args, capture_output=True, text=True, cwd=initialdir)
            if out.returncode != 0 or not out.stdout.strip():
                return None
            return out.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError(_ZENITY_NOT_FOUND) from None


def get_default_file_opener() -> FileFolderOpener:
    """Return an opener suitable for the current platform (Tkinter on Windows, Zenity on Linux)."""
    if sys.platform == "win32":
        return TkinterFileOpener()
    return ZenityFileOpener()


class HeadlessFileOpener(FileFolderOpener):
    """Returns pre-configured paths for artifact/Docker mode (no GUI dialogs)."""

    def __init__(
        self,
        open_dirs: Optional[List[str]] = None,
        open_files: Optional[List[str]] = None,
        save_file: Optional[str] = None,
    ) -> None:
        self._open_dirs = open_dirs or []
        self._open_files = open_files or []
        self._save_file = save_file

    def ask_open_dirs(self, initialdir: str = ".") -> List[str]:
        return list(self._open_dirs)

    def ask_open_files(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> List[str]:
        return list(self._open_files)

    def ask_save_file(
        self,
        initialdir: str = ".",
        filetypes: Optional[FileTypes] = None,
    ) -> Optional[str]:
        return self._save_file


def get_artifact_file_opener(
    open_dirs: Optional[List[str]] = None,
    open_files: Optional[List[str]] = None,
    save_file: Optional[str] = None,
) -> FileFolderOpener:
    return HeadlessFileOpener(
        open_dirs=open_dirs,
        open_files=open_files,
        save_file=save_file,
    )
