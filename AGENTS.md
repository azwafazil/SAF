# Repository Guidelines

## Project Structure & Module Organization

SAF is a Python package using a `src/` layout. Core code lives in `src/saf_mcp/`: `server.py` defines MCP tools, resources, prompts, and the CLI entry point; `security.py` contains sandbox and extension validation; `spss_utils.py` wraps SPSS/tabular read, write, preview, and profiling behavior. Tests live in `tests/`. User-facing docs are in `README.md` and `docs/`; sample client configuration and prompts are in `examples/`. Keep real datasets outside the repository, preferably under a local directory referenced by `SAF_DATA_ROOT`.

## Build, Test, and Development Commands

Create and activate a local environment before development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run tests with:

```bash
pytest
```

Run the MCP server locally with the default stdio transport:

```bash
SAF_DATA_ROOT=/absolute/path/to/saf-data python -m saf_mcp.server
```

After editable install, `saf-mcp` runs the same entry point. Use `MCP_TRANSPORT=streamable-http saf-mcp` only when the installed `mcp` package supports that transport.

## Coding Style & Naming Conventions

Use Python 3.10+ syntax and keep type hints on public helpers and MCP tool functions. Follow the existing style: 4-space indentation, module-level constants in `UPPER_SNAKE_CASE`, functions in `snake_case`, and structured result dictionaries using `_success()` and `_error()`. Keep MCP tool handlers thin; place reusable file, dataframe, and security logic in helper modules. Preserve local-first privacy behavior when adding features.

## Testing Guidelines

Tests use `pytest`, configured in `pyproject.toml` with `tests/` as the test path and `src/` on `pythonpath`. Name test files `test_*.py` and test functions `test_*`. For path handling or filesystem behavior, prefer `tmp_path` and `monkeypatch` to avoid writing outside the test sandbox. Add regression tests for security boundaries, extension validation, and new MCP tool behavior.

## Commit & Pull Request Guidelines

Recent history uses short, imperative commit messages such as `Support configurable HTTP host and port` and `Forge SAF MCP starter`. Keep commits focused and describe the behavior changed. Pull requests should include a concise summary, test results (`pytest` output is enough), linked issues when applicable, and notes for any security, dataset handling, or MCP transport changes.

## Security & Configuration Tips

Never commit `.sav`, `.zsav`, `.por`, `.csv`, or `.tsv` files; `.gitignore` blocks these because they may contain sensitive respondent records. All dataset paths must remain under `SAF_DATA_ROOT`, and generated SPSS syntax must stay text-only. Do not add shell execution or external data upload paths.
