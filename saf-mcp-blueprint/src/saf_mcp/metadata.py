from __future__ import annotations

from typing import Any

import pandas as pd

from .io import read_dataset


def _infer_measure(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        unique = series.dropna().nunique()
        if unique <= 10:
            return "ordinal_or_nominal"
        return "scale"
    return "nominal"


def metadata_to_dict(meta: Any | None) -> dict[str, Any]:
    if meta is None:
        return {}
    wanted = [
        "column_names",
        "column_labels",
        "variable_value_labels",
        "missing_ranges",
        "missing_user_values",
        "variable_measure",
        "original_variable_types",
        "number_rows",
        "number_columns",
        "file_label",
        "notes",
    ]
    output: dict[str, Any] = {}
    for name in wanted:
        if hasattr(meta, name):
            value = getattr(meta, name)
            try:
                output[name] = value
            except Exception:
                output[name] = str(value)
    return output


def data_dictionary(file: str) -> dict[str, Any]:
    df, meta = read_dataset(file)
    meta_dict = metadata_to_dict(meta)
    rows: list[dict[str, Any]] = []
    labels = meta_dict.get("column_labels") or []
    value_labels = meta_dict.get("variable_value_labels") or {}
    measure = meta_dict.get("variable_measure") or {}

    for i, col in enumerate(df.columns):
        rows.append(
            {
                "name": col,
                "label": labels[i] if isinstance(labels, list) and i < len(labels) else None,
                "dtype": str(df[col].dtype),
                "missing": int(df[col].isna().sum()),
                "unique": int(df[col].nunique(dropna=True)),
                "suggested_measure": measure.get(col) if isinstance(measure, dict) and col in measure else _infer_measure(df[col]),
                "value_labels": value_labels.get(col, {}) if isinstance(value_labels, dict) else {},
            }
        )
    return {"ok": True, "file": file, "n_rows": len(df), "n_columns": df.shape[1], "variables": rows}
