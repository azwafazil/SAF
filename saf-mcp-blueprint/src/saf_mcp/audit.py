from __future__ import annotations

import hashlib
import platform
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def audit_record(dataset_path: Path, tool: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset_path.name,
        "dataset_sha256": file_sha256(dataset_path) if dataset_path.exists() else None,
        "tool": tool,
        "params": params,
        "python": platform.python_version(),
        "packages": {
            "pandas": package_version("pandas"),
            "numpy": package_version("numpy"),
            "scipy": package_version("scipy"),
            "statsmodels": package_version("statsmodels"),
            "pingouin": package_version("pingouin"),
            "pyreadstat": package_version("pyreadstat"),
        },
    }
