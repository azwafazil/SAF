# JSON-RPC Examples

The SAF MCP server speaks [Model Context Protocol](https://modelcontextprotocol.io/)
over `stdio` (default) or streamable HTTP. Each tool call is a JSON-RPC 2.0
`tools/call` request. The examples below use `curl` against a local
streamable-HTTP server, but the same payloads work over stdio framed
records.

## 1. Start the server

```bash
export SAF_DATA_ROOT=/absolute/path/to/saf-data
saf-mcp                # stdio (Claude Desktop / MCP clients)
# or
MCP_TRANSPORT=streamable-http saf-mcp   # HTTP on default port
```

## 2. List available tools

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

Returns all 19 tools (7 dataset + 12 `saf_stat_*`) plus the two resources
and the prompt.

## 3. Inspect a `.sav` file

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "inspect_spss_metadata",
    "arguments": {
      "path": "survey.sav"
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"ok\": true, \"path\": \"survey.sav\", \"metadata\": {\"row_count\": 1234, \"column_count\": 17, \"columns\": [\"id\", \"age\", \"income\", ...], ...}}"
      }
    ]
  }
}
```

## 4. Run a Welch t-test with effect size

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "saf_stat_compare_groups",
    "arguments": {
      "path": "study.csv",
      "value_col": "income",
      "group_col": "sex",
      "parametric": true,
      "equal_var": false
    }
  }
}
```

The response includes `method`, `t_stat`, `p_value`, `cohens_d`, and
`hedges_g` (small-sample-corrected Cohen's d).

## 5. One-way ANOVA with Tukey HSD post-hoc

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "saf_stat_anova",
    "arguments": {
      "path": "study.csv",
      "value_col": "score",
      "group_col": "group",
      "welch": false,
      "post_hoc": true
    }
  }
}
```

## 6. Correlation with bootstrap CI (Spearman)

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "saf_stat_correlate",
    "arguments": {
      "path": "study.csv",
      "x": "age",
      "y": "income",
      "method": "spearman",
      "bootstrap": 1000,
      "seed": 42
    }
  }
}
```

Returns `r`, `p_value`, and `ci95` computed from 1000 percentile-bootstrap
resamples (reproducible with `seed`).

## 7. Power analysis (one-way F-test)

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "saf_stat_power",
    "arguments": {
      "test": "f",
      "effect_size": 0.25,
      "alpha": 0.05,
      "power": 0.8,
      "df_num": 2
    }
  }
}
```

Solves for `solved_nobs` (total sample size) given Cohen's *f* = 0.25,
*k* = 3 groups, target power 0.8.

## 8. Detect outliers (Mahalanobis, multi-column)

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "saf_stat_outliers",
    "arguments": {
      "path": "study.csv",
      "columns": ["age", "income", "score"],
      "method": "mahalanobis"
    }
  }
}
```

Returns per-row Mahalanobis distances and an outlier flag using the
chi-squared cutoff at 97.5% with `df = number of columns`.

## 9. Read a resource

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "resources/read",
  "params": { "uri": "saf://guide" }
}
```

## 10. Render the analysis prompt

```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "method": "prompts/get",
  "params": {
    "name": "analyze_dataset_prompt",
    "arguments": { "path": "study.sav" }
  }
}
```

## Error envelope

All tools return `{"ok": false, "error": {"type": "...", "message": "..."}}`
on failure rather than raising — the agent can keep the session alive and
route the error to the operator or the model.

## Security note

`SAF_DATA_ROOT` is the only directory the server will read from or write to.
Path traversal (`../../etc/passwd`) is rejected with a `SAFSecurityError`,
and file extensions are validated before any read or write.
