"""SPSS-compatible dataset helpers backed by pyreadstat."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pyreadstat

from .security import SPSS_EXTENSIONS, TABULAR_EXTENSIONS, extension_for


def read_spss(path: Path, *, rows: int | None = None, metadata_only: bool = False):
    ext = extension_for(path)
    if ext not in SPSS_EXTENSIONS:
        raise ValueError(f"Expected an SPSS-compatible file, got {ext}.")

    kwargs: dict[str, Any] = {}
    if rows is not None:
        kwargs["row_limit"] = rows
    if metadata_only:
        kwargs["metadataonly"] = True

    if ext == ".por":
        return pyreadstat.read_por(str(path), **kwargs)
    return pyreadstat.read_sav(str(path), **kwargs)


def metadata_to_dict(metadata: Any) -> dict[str, Any]:
    names = list(getattr(metadata, "column_names", []) or [])
    labels = list(getattr(metadata, "column_labels", []) or [])
    label_by_name = {
        name: labels[index] for index, name in enumerate(names) if index < len(labels)
    }

    return {
        "row_count": getattr(metadata, "number_rows", None),
        "column_count": getattr(metadata, "number_columns", len(names)),
        "columns": names,
        "column_labels": label_by_name,
        "file_label": getattr(metadata, "file_label", None),
        "file_encoding": getattr(metadata, "file_encoding", None),
        "variable_value_labels": getattr(metadata, "variable_value_labels", {}) or {},
        "variable_measure": getattr(metadata, "variable_measure", {}) or {},
        "variable_format": getattr(metadata, "variable_format", {}) or {},
        "original_variable_types": getattr(metadata, "original_variable_types", {}) or {},
        "readstat_variable_types": getattr(metadata, "readstat_variable_types", {}) or {},
    }


def dataframe_preview(df: pd.DataFrame) -> dict[str, Any]:
    safe_df = df.where(pd.notnull(df), None)
    return {
        "row_count": int(len(safe_df)),
        "columns": list(safe_df.columns),
        "rows": safe_df.to_dict(orient="records"),
    }


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": {},
    }

    for column in df.columns:
        series = df[column]
        column_profile: dict[str, Any] = {
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "non_missing_count": int(series.notna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_numeric_dtype(series):
            described = series.describe()
            for key in ["mean", "std", "min", "25%", "50%", "75%", "max"]:
                value = described.get(key)
                column_profile[key] = None if pd.isna(value) else float(value)
        else:
            values = series.dropna().astype(str)
            top_values = values.value_counts().head(10)
            column_profile["top_values"] = {
                str(index): int(value) for index, value in top_values.items()
            }

        profile["columns"][str(column)] = column_profile

    return profile


def read_tabular(path: Path) -> pd.DataFrame:
    ext = extension_for(path)
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    raise ValueError(f"Expected a CSV or TSV file, got {ext}.")


def write_csv(df: pd.DataFrame, output_path: Path) -> None:
    df.to_csv(output_path, index=False)


def write_sav(df: pd.DataFrame, output_path: Path) -> None:
    pyreadstat.write_sav(df, str(output_path))


def basic_spss_syntax(dataset_path: str, variables: list[str] | None = None) -> str:
    variable_clause = " ".join(variables) if variables else "ALL"
    return "\n".join(
        [
            f"GET FILE='{dataset_path}'.",
            "DATASET NAME SAFDataset.",
            f"DISPLAY DICTIONARY /VARIABLES={variable_clause}.",
            f"FREQUENCIES VARIABLES={variable_clause}.",
            "EXECUTE.",
        ]
    )
