from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_root: Path
    allow_write: bool = False
    max_file_mb: int = 100


def get_settings() -> Settings:
    root = Path(os.getenv("SAF_DATA_ROOT", "./data")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    allow_write = os.getenv("SAF_ALLOW_WRITE", "0") in {"1", "true", "TRUE", "yes", "YES"}
    max_file_mb = int(os.getenv("SAF_MAX_FILE_MB", "100"))
    return Settings(data_root=root, allow_write=allow_write, max_file_mb=max_file_mb)
