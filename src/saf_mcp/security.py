"""Filesystem and extension safety helpers for SAF."""

from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT_ENV = "SAF_DATA_ROOT"

SPSS_EXTENSIONS = {".sav", ".zsav", ".por"}
TABULAR_EXTENSIONS = {".csv", ".tsv", ".xlsx"}
SUPPORTED_EXTENSIONS = SPSS_EXTENSIONS | TABULAR_EXTENSIONS


class SAFSecurityError(ValueError):
    """Raised when a path or file extension violates SAF safety rules."""


def get_data_root() -> Path:
    """Return the sandbox root used for all dataset access."""
    raw_root = os.environ.get(DATA_ROOT_ENV)
    root = Path(raw_root).expanduser() if raw_root else Path.cwd()
    return root.resolve()


def extension_for(path: str | Path) -> str:
    return Path(path).suffix.lower()


def validate_extension(path: str | Path, allowed: set[str] | None = None) -> str:
    ext = extension_for(path)
    allowed_extensions = allowed or SUPPORTED_EXTENSIONS
    if ext not in allowed_extensions:
        allowed_display = ", ".join(sorted(allowed_extensions))
        raise SAFSecurityError(
            f"Unsupported file extension '{ext or '<none>'}'. Allowed: {allowed_display}."
        )
    return ext


def resolve_dataset_path(path: str | Path, allowed: set[str] | None = None) -> Path:
    """Resolve a user path and ensure it remains inside SAF_DATA_ROOT."""
    validate_extension(path, allowed)
    root = get_data_root()
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()

    if resolved != root and root not in resolved.parents:
        raise SAFSecurityError(
            f"Path traversal blocked. Files must stay under {DATA_ROOT_ENV}={root}."
        )
    return resolved


def require_existing_dataset(path: str | Path, allowed: set[str] | None = None) -> Path:
    resolved = resolve_dataset_path(path, allowed)
    if not resolved.exists():
        raise FileNotFoundError(f"Dataset not found under {DATA_ROOT_ENV}: {path}")
    if not resolved.is_file():
        raise SAFSecurityError(f"Dataset path is not a file: {path}")
    return resolved


def resolve_output_path(path: str | Path, allowed: set[str] | None = None) -> Path:
    resolved = resolve_dataset_path(path, allowed)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(get_data_root()))
