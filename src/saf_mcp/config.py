"""Centralized SAF configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

SAF_HOST = os.environ.get("SAF_HOST", "127.0.0.1")
SAF_PORT = int(os.environ.get("SAF_PORT", "8000"))
SAF_DATA_ROOT = os.environ.get("SAF_DATA_ROOT", "")
SAF_ALLOW_WRITE = os.environ.get("SAF_ALLOW_WRITE", "0") == "1"
SAF_AUDIT_LOG = os.environ.get("SAF_AUDIT_LOG", "")
SAF_MAX_PREVIEW_ROWS = int(os.environ.get("SAF_MAX_PREVIEW_ROWS", "500"))
SAF_MAX_PROFILE_ROWS = int(os.environ.get("SAF_MAX_PROFILE_ROWS", "100000"))


def get_data_root() -> Path:
    root = Path(SAF_DATA_ROOT).expanduser() if SAF_DATA_ROOT else Path.cwd()
    return root.resolve()
