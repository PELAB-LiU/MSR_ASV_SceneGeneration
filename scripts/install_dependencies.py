"""Install Python dependencies from package.json with OS-specific packages."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _platform_key() -> str:
    system = sys.platform
    if system.startswith("linux"):
        return "linux"
    if system == "darwin":
        return "darwin"
    if system == "win32":
        return "win32"
    raise RuntimeError(f"Unsupported platform: {system}")


def _load_dependencies(package_json_path: Path) -> list[str]:
    with package_json_path.open(encoding="utf-8") as package_file:
        package_data = json.load(package_file)

    python_dependencies = package_data.get("pythonDependencies", {})
    common = python_dependencies.get("common", [])
    platform_specific = python_dependencies.get("platformSpecific", {})
    platform_key = _platform_key()
    platform_packages = platform_specific.get(platform_key, [])

    return [*common, *platform_packages]


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    package_json_path = repo_root / "package.json"
    if not package_json_path.is_file():
        print(f"Error: {package_json_path} not found.", file=sys.stderr)
        return 1

    dependencies = _load_dependencies(package_json_path)
    platform_key = _platform_key()
    print(f"Detected platform: {platform_key}")
    print(f"Installing {len(dependencies)} packages...")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *dependencies],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
