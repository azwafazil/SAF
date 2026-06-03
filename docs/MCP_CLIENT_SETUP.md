# MCP Client Setup

SAF runs as a local MCP server over stdio by default. Keep datasets outside the repository and point clients at a sandbox directory with `SAF_DATA_ROOT`.

## Codex CLI

From this checkout, install SAF and register it with Codex:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
mkdir -p /root/saf-data
codex mcp add saf --env SAF_DATA_ROOT=/root/saf-data -- /absolute/path/to/SAF/.venv/bin/saf-mcp
codex mcp list
```

Codex will launch SAF on demand as a stdio MCP server.

## Hermes Agent

Hermes can use the same stdio command. Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  saf:
    command: /absolute/path/to/SAF/.venv/bin/saf-mcp
    env:
      SAF_DATA_ROOT: /root/saf-data
    timeout: 180
    connect_timeout: 60
```

Restart Hermes after changing the config:

```bash
hermes gateway restart
hermes mcp test saf
```

Expected discovery includes the dataset tools (`list_data_files`, `inspect_spss_metadata`, `preview_spss_data`, `profile_spss_data`, `convert_spss_to_csv`, `convert_csv_to_sav`, `generate_basic_spss_syntax`) plus the `saf_stat_*` statistical analysis tools.

## E2E Smoke Test

Place a small CSV under `SAF_DATA_ROOT`, then call the MCP tools in this order:

1. `list_data_files`
2. `convert_csv_to_sav`
3. `inspect_spss_metadata`
4. `preview_spss_data`
5. `profile_spss_data`
6. `generate_basic_spss_syntax`
7. `convert_spss_to_csv`

All input and output paths must be relative to `SAF_DATA_ROOT`.
