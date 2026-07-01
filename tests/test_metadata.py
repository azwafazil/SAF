"""Tests for the SPSS-style Data Dictionary (metadata.py)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from saf_mcp.metadata import build_data_dictionary
from saf_mcp.spss_utils import metadata_to_dict


@pytest.fixture
def csv_dataset():
    tmp = Path(tempfile.mkdtemp(prefix="saf-test-meta-"))
    os.environ["SAF_DATA_ROOT"] = str(tmp)
    n = 100
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "id": range(1, n + 1),
            "age": rng.integers(18, 70, n).astype(float),
            "income": rng.normal(50000, 15000, n).round(2),
            "score": rng.normal(75, 10, n).round(2),
            "group": rng.choice(["Control", "Treatment"], n),
            "satisfied": rng.choice([0, 1], n),
            "education": rng.choice([1, 2, 3, 4, 5], n),
        }
    )
    df.loc[rng.choice(n, 5, replace=False), "income"] = np.nan
    path = tmp / "test_data.csv"
    df.to_csv(path, index=False)
    return tmp, "test_data.csv"


def test_inspect_dataset_csv_basic(csv_dataset):
    """Build data dictionary from a CSV file."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    assert result["ok"] is True
    assert result["file_info"]["rows"] == 100
    assert result["file_info"]["columns"] == 7
    assert len(result["variables"]) == 7


def test_inspect_dataset_variable_names(csv_dataset):
    """All variable names are present."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    names = [v["name"] for v in result["variables"]]
    assert "id" in names
    assert "age" in names
    assert "income" in names
    assert "score" in names
    assert "group" in names


def test_inspect_dataset_measure_inference(csv_dataset):
    """Measurement levels are correctly inferred."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    measures = {v["name"]: v["measure"] for v in result["variables"]}
    assert measures["id"] == "scale"
    assert measures["age"] == "scale"
    assert measures["income"] == "scale"
    assert measures["score"] == "scale"
    assert measures["group"] == "nominal"
    assert measures["satisfied"] == "nominal"


def test_inspect_dataset_role_suggestion(csv_dataset):
    """Research roles are plausibly suggested."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    roles = {v["name"]: v["role"] for v in result["variables"]}
    assert roles["id"] == "identifier"
    assert roles["satisfied"] in ("dependent_variable", "grouping")
    assert roles["group"] == "grouping"
    assert roles["age"] in ("independent_variable", "dependent_variable")


def test_inspect_dataset_missing_counts(csv_dataset):
    """Missing value counts are correct."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    income_meta = {v["name"]: v for v in result["variables"]}["income"]
    assert income_meta["n_missing"] == 5
    assert income_meta["pct_missing"] == 5.0
    assert income_meta["n"] == 95


def test_inspect_dataset_value_labels_empty_for_csv(csv_dataset):
    """CSV files have no value labels (empty dict)."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    group_meta = {v["name"]: v for v in result["variables"]}["group"]
    assert group_meta["value_labels"] == {}


def test_inspect_dataset_numeric_stats(csv_dataset):
    """Numeric variables include min/max/mean/std."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    age_meta = {v["name"]: v for v in result["variables"]}["age"]
    assert "min" in age_meta
    assert "max" in age_meta
    assert "mean" in age_meta
    assert "std" in age_meta
    assert 18 <= age_meta["min"] <= 70
    assert 18 <= age_meta["max"] <= 70


def test_inspect_dataset_unique_counts(csv_dataset):
    """Unique value counts are correct."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    id_meta = {v["name"]: v for v in result["variables"]}["id"]
    group_meta = {v["name"]: v for v in result["variables"]}["group"]
    assert id_meta["n_unique"] == 100
    assert group_meta["n_unique"] == 2


def test_inspect_dataset_warnings(csv_dataset):
    """Data quality warnings are generated."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    assert isinstance(result["warnings"], list)


def test_inspect_dataset_sample_values(csv_dataset):
    """Sample values are included for each variable."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    for v in result["variables"]:
        assert "sample_values" in v
        assert isinstance(v["sample_values"], list)


def test_inspect_dataset_ordinal_likert(csv_dataset):
    """Education (1-5) should be detected as ordinal."""
    tmp, path = csv_dataset
    result = build_data_dictionary(path)
    edu_meta = {v["name"]: v for v in result["variables"]}["education"]
    assert edu_meta["measure"] == "ordinal"


@pytest.fixture
def spss_metadata_stub():
    return {
        "row_count": 100,
        "column_count": 3,
        "columns": ["q1", "q2", "q3"],
        "column_labels": {
            "q1": "I am satisfied with the service",
            "q2": "I would recommend this service",
            "q3": "Overall rating",
        },
        "variable_value_labels": {
            "q1": {1: "Strongly Disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly Agree"},
            "q2": {1: "No", 2: "Yes"},
            "q3": {1: "Poor", 2: "Fair", 3: "Good", 4: "Excellent"},
        },
        "variable_measure": {"q1": "ordinal", "q2": "nominal", "q3": "ordinal"},
        "variable_format": {"q1": "F5.0", "q2": "F5.0", "q3": "F5.0"},
        "missing_ranges": {},
    }


def test_metadata_to_dict_includes_missing_ranges():
    """metadata_to_dict now returns missing_ranges key."""
    from collections import namedtuple

    MockMeta = namedtuple("MockMeta", [
        "column_names", "column_labels", "number_rows", "number_columns",
        "file_label", "file_encoding", "variable_value_labels",
        "variable_measure", "variable_format", "original_variable_types",
        "readstat_variable_types", "missing_ranges",
    ])
    meta = MockMeta(
        column_names=["a", "b"],
        column_labels=["", ""],
        number_rows=10,
        number_columns=2,
        file_label="test",
        file_encoding="UTF-8",
        variable_value_labels={},
        variable_measure={},
        variable_format={},
        original_variable_types={},
        readstat_variable_types={},
        missing_ranges={"a": [(1, 3)]},
    )
    result = metadata_to_dict(meta)
    assert "missing_ranges" in result
    assert result["missing_ranges"]["a"] == [{"lo": 1.0, "hi": 3.0}]
