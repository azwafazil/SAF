from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .security import require_supported_read, require_write_allowed, safe_path


def list_data_files() -> list[dict[str, Any]]:
    root = safe_path(".", must_exist=True)
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".csv", ".tsv", ".xlsx", ".xls", ".sav", ".zsav", ".por"}:
            files.append(
                {
                    "name": str(path.relative_to(root)),
                    "extension": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                }
            )
    return files


def read_dataset(file: str, *, apply_value_formats: bool = False) -> tuple[pd.DataFrame, Any | None]:
    path = safe_path(file, must_exist=True)
    require_supported_read(path)
    ext = path.suffix.lower()

    if ext == ".csv":
        return pd.read_csv(path), None
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t"), None
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path), None
    if ext in {".sav", ".zsav"}:
        import pyreadstat

        df, meta = pyreadstat.read_sav(str(path), apply_value_formats=apply_value_formats)
        return df, meta
    if ext == ".por":
        import pyreadstat

        df, meta = pyreadstat.read_por(str(path), apply_value_formats=apply_value_formats)
        return df, meta
    raise ValueError(f"Unsupported file type: {ext}")


def write_sav_from_csv(input_csv: str, output_sav: str, *, column_labels: dict[str, str] | None = None) -> dict[str, Any]:
    import pyreadstat

    df, _ = read_dataset(input_csv)
    out = require_write_allowed(output_sav)
    pyreadstat.write_sav(df, str(out), column_labels=column_labels)
    return {"ok": True, "output": str(out.name), "rows": len(df), "columns": list(df.columns)}


def write_csv_from_sav(input_sav: str, output_csv: str) -> dict[str, Any]:
    df, _ = read_dataset(input_sav)
    out = require_write_allowed(output_csv)
    df.to_csv(out, index=False)
    return {"ok": True, "output": str(out.name), "rows": len(df), "columns": list(df.columns)}
