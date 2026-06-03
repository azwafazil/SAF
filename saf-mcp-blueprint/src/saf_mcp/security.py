from __future__ import annotations

from pathlib import Path

from .config import get_settings

SUPPORTED_READ_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".sav", ".zsav", ".por"}
SUPPORTED_WRITE_EXTENSIONS = {".csv", ".xlsx", ".sav", ".md", ".json"}


class SAFSecurityError(ValueError):
    """Raised when SAF blocks unsafe file access."""


def safe_path(relative_path: str | Path, *, must_exist: bool = True) -> Path:
    """Resolve a user path under SAF_DATA_ROOT and prevent path traversal."""
    settings = get_settings()
    candidate = (settings.data_root / Path(relative_path)).resolve()
    if settings.data_root not in candidate.parents and candidate != settings.data_root:
        raise SAFSecurityError(f"Path escapes SAF_DATA_ROOT: {relative_path}")
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"File not found under SAF_DATA_ROOT: {relative_path}")
    return candidate


def require_supported_read(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_READ_EXTENSIONS:
        raise SAFSecurityError(f"Unsupported file extension: {path.suffix}")
    settings = get_settings()
    max_bytes = settings.max_file_mb * 1024 * 1024
    if path.exists() and path.stat().st_size > max_bytes:
        raise SAFSecurityError(f"File too large. Limit is {settings.max_file_mb} MB")


def require_write_allowed(output_path: str | Path) -> Path:
    settings = get_settings()
    if not settings.allow_write:
        raise SAFSecurityError("Write blocked. Set SAF_ALLOW_WRITE=1 to enable exports.")
    path = safe_path(output_path, must_exist=False)
    if path.suffix.lower() not in SUPPORTED_WRITE_EXTENSIONS:
        raise SAFSecurityError(f"Unsupported output extension: {path.suffix}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
