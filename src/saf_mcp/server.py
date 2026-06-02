"""SAF MCP server."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .security import (
    SPSS_EXTENSIONS,
    TABULAR_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    SAFSecurityError,
    get_data_root,
    relative_to_root,
    require_existing_dataset,
    resolve_output_path,
)
from .spss_utils import (
    basic_spss_syntax,
    dataframe_preview,
    metadata_to_dict,
    profile_dataframe,
    read_spss,
    read_tabular,
    write_csv,
    write_sav,
)

mcp = FastMCP("SAF")


def _error(error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
        },
    }


def _success(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


@mcp.tool()
def list_data_files() -> dict[str, Any]:
    """List supported dataset files under SAF_DATA_ROOT."""
    try:
        root = get_data_root()
        if not root.exists():
            return _success(data_root=str(root), files=[])

        files = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(
                    {
                        "path": relative_to_root(path),
                        "extension": path.suffix.lower(),
                        "size_bytes": path.stat().st_size,
                    }
                )
        return _success(data_root=str(root), files=sorted(files, key=lambda item: item["path"]))
    except Exception as exc:  # noqa: BLE001 - MCP tools should return structured errors.
        return _error(exc)


@mcp.tool()
def inspect_spss_metadata(path: str) -> dict[str, Any]:
    """Inspect metadata for a .sav, .zsav, or .por file."""
    try:
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        _, metadata = read_spss(dataset_path, metadata_only=True)
        return _success(path=relative_to_root(dataset_path), metadata=metadata_to_dict(metadata))
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def preview_spss_data(path: str, rows: int = 20) -> dict[str, Any]:
    """Preview rows from a .sav, .zsav, or .por file."""
    try:
        if rows < 1 or rows > 500:
            raise ValueError("rows must be between 1 and 500.")
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        df, metadata = read_spss(dataset_path, rows=rows)
        return _success(
            path=relative_to_root(dataset_path),
            requested_rows=rows,
            preview=dataframe_preview(df),
            metadata=metadata_to_dict(metadata),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def profile_spss_data(path: str, rows: int | None = 5000) -> dict[str, Any]:
    """Profile variables in a .sav, .zsav, or .por file."""
    try:
        if rows is not None and (rows < 1 or rows > 100000):
            raise ValueError("rows must be between 1 and 100000, or null.")
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        df, metadata = read_spss(dataset_path, rows=rows)
        return _success(
            path=relative_to_root(dataset_path),
            sampled_rows=rows,
            profile=profile_dataframe(df),
            metadata=metadata_to_dict(metadata),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def convert_spss_to_csv(path: str, output_path: str) -> dict[str, Any]:
    """Convert a .sav, .zsav, or .por file to CSV inside SAF_DATA_ROOT."""
    try:
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        csv_path = resolve_output_path(output_path, {".csv"})
        df, _ = read_spss(dataset_path)
        write_csv(df, csv_path)
        return _success(
            input_path=relative_to_root(dataset_path),
            output_path=relative_to_root(csv_path),
            rows_written=int(len(df)),
            columns_written=int(len(df.columns)),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def convert_csv_to_sav(path: str, output_path: str) -> dict[str, Any]:
    """Convert a CSV or TSV file to .sav inside SAF_DATA_ROOT."""
    try:
        tabular_path = require_existing_dataset(path, TABULAR_EXTENSIONS)
        sav_path = resolve_output_path(output_path, {".sav"})
        df = read_tabular(tabular_path)
        write_sav(df, sav_path)
        return _success(
            input_path=relative_to_root(tabular_path),
            output_path=relative_to_root(sav_path),
            rows_written=int(len(df)),
            columns_written=int(len(df.columns)),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def generate_basic_spss_syntax(path: str, variables: list[str] | None = None) -> dict[str, Any]:
    """Generate basic SPSS syntax without executing it."""
    try:
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        if variables is not None:
            _, metadata = read_spss(dataset_path, metadata_only=True)
            known_variables = set(metadata_to_dict(metadata)["columns"])
            unknown = sorted(set(variables) - known_variables)
            if unknown:
                raise ValueError(f"Unknown variables: {', '.join(unknown)}")
        syntax = basic_spss_syntax(relative_to_root(dataset_path), variables)
        return _success(path=relative_to_root(dataset_path), syntax=syntax)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.resource("saf://guide")
def guide() -> str:
    return (
        "SAF -- Statistical Analysis Forge -- is a privacy-first MCP server for "
        "SPSS-compatible datasets. Use it to inspect metadata, preview rows, profile "
        "variables, convert files, and generate basic SPSS syntax. SAF does not execute "
        "SPSS syntax and does not access files outside SAF_DATA_ROOT."
    )


@mcp.resource("saf://repo-ingestion")
def repo_ingestion() -> str:
    return (
        "Keep real respondent datasets out of git. Place .sav, .zsav, .por, .csv, and "
        ".tsv files in SAF_DATA_ROOT, then reference paths relative to that directory. "
        "The server validates extensions and blocks traversal outside the sandbox."
    )


@mcp.prompt()
def analyze_dataset_prompt(path: str) -> str:
    return (
        "Analyze the SPSS-compatible dataset at this SAF sandbox path: "
        f"{path}\n\n"
        "First inspect metadata, then preview a small number of rows, then profile "
        "variables. Do not request data outside SAF_DATA_ROOT. Summarize data quality, "
        "missingness, notable labels, and reasonable next analysis steps."
    )


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    try:
        mcp.run(transport=transport)
    except TypeError as exc:
        if transport == "streamable-http":
            raise RuntimeError(
                "Installed MCP package does not support MCP_TRANSPORT=streamable-http. "
                "Upgrade mcp[cli] or run with the default stdio transport."
            ) from exc
        raise


if __name__ == "__main__":
    main()
