"""SPSS-style Data Dictionary — Variable View for SAF.

Generates rich variable metadata with:
  - variable name, label, value labels
  - measure level (nominal, ordinal, scale)
  - data type, unique count, missing %
  - suggested role (IV, DV, control, scale item, identifier)

Works for both SPSS (.sav/.zsav/.por) and tabular (.csv/.tsv/.xlsx) files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .security import (
    SPSS_EXTENSIONS,
    TABULAR_EXTENSIONS,
    extension_for,
    require_existing_dataset,
)
from .spss_utils import read_spss, read_tabular


def _load_dataframe(path: str) -> pd.DataFrame:
    p = Path(path)
    ext = extension_for(p)
    if ext in SPSS_EXTENSIONS:
        resolved = require_existing_dataset(path, SPSS_EXTENSIONS)
        df, _ = read_spss(resolved)
        return df
    if ext in TABULAR_EXTENSIONS:
        resolved = require_existing_dataset(path, TABULAR_EXTENSIONS)
        return read_tabular(resolved)
    resolved = require_existing_dataset(path)
    if ext in (".sav", ".zsav", ".por"):
        df, _ = read_spss(resolved)
        return df
    return read_tabular(resolved)


def _suggest_role(
    name: str,
    dtype: str,
    n_unique: int,
    n_total: int,
    measure: str | None,
    has_value_labels: bool,
    label: str | None,
) -> str:
    """Heuristic to suggest a variable's role in a research context."""
    name_lower = name.lower().strip()
    label_lower = (label or "").lower().strip()

    # Identifiers / admin columns
    if name_lower in ("id", "subject", "subjectid", "respondent", "respondentid",
                      "participant", "participantid", "caseid", "casenumber",
                      "index", "rowid", "recordid", "code"):
        return "identifier"

    # Scale items (Likert, questionnaire items)
    if label_lower.startswith(("item", "scale", "subscale")) or "item" in label_lower:
        return "scale_item"
    if name_lower.startswith(("q", "item", "i_")) and n_unique <= 10:
        return "scale_item"

    # Measure level from SPSS metadata
    if measure == "nominal":
        if n_unique == 2:
            return "grouping"
        return "independent_variable"
    if measure == "ordinal":
        return "ordinal_predictor"
    if measure == "scale":
        if n_unique <= 5:
            return "ordinal_predictor"
        if name_lower in (
            "score", "total", "sum", "mean", "average", "dv", "outcome",
            "result", "gpa", "grade", "mark",
        ):
            return "dependent_variable"
        return "independent_variable"

    # Two unique values: binary or grouping
    if n_unique == 2:
        if "int" in dtype:
            return "dependent_variable"
        return "grouping"

    # Fallback by dtype and cardinality
    if "int" in dtype or "float" in dtype:
        if n_unique <= 5:
            return "ordinal_predictor"
        if n_unique <= 15:
            return "grouping"
        return "independent_variable"

    # String / categorical
    if n_unique <= 2:
        return "grouping"
    if n_unique <= 20:
        return "independent_variable"
    return "categorical_predictor"


def _infer_measure(
    series: pd.Series,
    spss_measure: str | None,
    n_unique: int,
    n_total: int,
) -> str:
    """Infer measurement level: nominal / ordinal / scale."""
    if spss_measure and spss_measure.lower() in ("nominal", "ordinal", "scale"):
        return spss_measure.lower()

    if not pd.api.types.is_numeric_dtype(series):
        return "nominal"

    if series.dropna().nunique() <= 2:
        return "nominal"

    # Likert-like: integer with 3–10 values
    if n_unique <= 10 and n_unique >= 3:
        unique_vals = sorted(series.dropna().unique())
        try:
            if all(float(v).is_integer() for v in unique_vals):
                return "ordinal"
        except (ValueError, TypeError):
            pass
        return "ordinal"

    return "scale"


def build_data_dictionary(
    path: str,
    spss_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an SPSS-style Variable View data dictionary.

    Parameters
    ----------
    path : str
        Dataset path relative to SAF_DATA_ROOT.
    spss_metadata : dict, optional
        Pre-read SPSS metadata from metadata_to_dict(). If None and the
        file is an SPSS type, it will be read automatically.

    Returns
    -------
    dict with keys: file_info, variables (list of variable dicts),
    warnings (list of data-quality notes).
    """
    df = _load_dataframe(path)
    n_rows = len(df)

    col_labels: dict[str, str] = {}
    col_value_labels: dict[str, dict[Any, str]] = {}
    col_measure: dict[str, str] = {}
    col_missing_rules: dict[str, list[Any]] = {}
    col_formats: dict[str, str] = {}
    file_label = None
    file_encoding = None

    if spss_metadata:
        col_labels = spss_metadata.get("column_labels", {}) or {}
        col_value_labels = spss_metadata.get("variable_value_labels", {}) or {}
        col_measure_raw = spss_metadata.get("variable_measure", {}) or {}
        col_measure = {k: v.lower() if v else "" for k, v in col_measure_raw.items()}
        col_missing_rules = spss_metadata.get("missing_ranges", {}) or {}
        col_formats = spss_metadata.get("variable_format", {}) or {}
        file_label = spss_metadata.get("file_label")
        file_encoding = spss_metadata.get("file_encoding")

    warnings: list[str] = []

    if n_rows == 0:
        warnings.append("Dataset is empty (0 rows).")

    variables: list[dict[str, Any]] = []

    for col in df.columns:
        series = df[col]
        valid = series.dropna()
        n_valid = len(valid)
        n_missing = int(series.isna().sum())
        pct_missing = round(100.0 * n_missing / n_rows, 2) if n_rows else 0.0
        n_unique = int(series.nunique(dropna=True))

        spss_measure = col_measure.get(col)
        measure = _infer_measure(series, spss_measure, n_unique, n_rows)

        label = col_labels.get(col) or ""
        value_labels = col_value_labels.get(col, {}) or {}

        if isinstance(value_labels, dict):
            formatted_value_labels = {str(k): str(v) for k, v in value_labels.items()}
        else:
            formatted_value_labels = {}

        role = _suggest_role(
            name=col,
            dtype=str(series.dtype),
            n_unique=n_unique,
            n_total=n_rows,
            measure=spss_measure,
            has_value_labels=bool(value_labels),
            label=label or None,
        )

        sample_values = valid.head(5).tolist()
        sample_values = [None if pd.isna(v) else v for v in sample_values]

        var_entry: dict[str, Any] = {
            "name": col,
            "label": label or "",
            "type": str(series.dtype),
            "measure": measure,
            "role": role,
            "n": int(n_valid),
            "n_missing": n_missing,
            "pct_missing": pct_missing,
            "n_unique": n_unique,
            "value_labels": formatted_value_labels,
            "format": col_formats.get(col, ""),
            "missing_values": col_missing_rules.get(col, []),
            "sample_values": sample_values,
        }

        if pd.api.types.is_numeric_dtype(series) and n_valid > 0:
            var_entry["min"] = float(valid.min())
            var_entry["max"] = float(valid.max())
            var_entry["mean"] = round(float(valid.mean()), 4)
            var_entry["std"] = round(float(valid.std(ddof=1)), 4)
        elif n_valid > 0:
            top = valid.value_counts().head(3)
            var_entry["top_values"] = {
                str(k): int(v) for k, v in top.items()
            }

        variables.append(var_entry)

        if n_missing > 0 and pct_missing > 20:
            warnings.append(
                f"'{col}' has {pct_missing}% missing — consider imputation or exclusion."
            )
        if measure == "nominal" and n_unique > 30:
            warnings.append(
                f"'{col}' is nominal with {n_unique} unique values — high cardinality."
            )
        if "float" in str(series.dtype) and n_unique <= 5 and measure == "scale":
            warnings.append(
                f"'{col}' is float with only {n_unique} unique values — maybe ordinal/categorical?"
            )

    return {
        "ok": True,
        "file_info": {
            "path": path,
            "rows": n_rows,
            "columns": len(df.columns),
            "file_label": file_label or "",
            "file_encoding": file_encoding or "",
        },
        "variables": variables,
        "warnings": warnings,
    }
