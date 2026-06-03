# SAF MCP — Statistical Analysis Forge

SAF MCP is an MCP server designed to become an **SPSS-compatible statistical assistant** for students, lecturers, and social-science researchers.

It is **not IBM SPSS** and it does not pretend to be an official replacement. Its goal is to cover the common academic workflow:

1. Import survey data from CSV/XLSX/SAV.
2. Preserve SPSS-style metadata: variable labels, value labels, missing values, measure level.
3. Run common analyses: descriptive statistics, frequencies, reliability, t-test, ANOVA, chi-square, correlation, regression, non-parametric tests.
4. Generate SPSS-like tables and APA-style interpretation.
5. Export reports and `.sav` files where possible.
6. Keep an audit trail so outputs are reproducible.

## Why SAF exists

SPSS is beginner-friendly but expensive. R/Python are powerful but intimidating. SAF MCP sits in the middle: the AI agent can call safe statistical tools while the codebase keeps results auditable.

## Current MVP tools in this scaffold

- `list_data_files`
- `inspect_dataset`
- `preview_dataset`
- `profile_dataset`
- `descriptive_statistics`
- `frequencies`
- `cronbach_alpha`
- `correlation_matrix`
- `t_test_independent`
- `one_way_anova`
- `chi_square_test`
- `ols_regression`
- `generate_spss_syntax`
- `run_analysis_recipe`
- `export_markdown_report`
- `convert_csv_to_sav`
- `convert_sav_to_csv`

## Install

```bash
git clone https://github.com/YOUR-USERNAME/SAF.git
cd SAF
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
mkdir -p data outputs
```

## Run locally

```bash
SAF_DATA_ROOT=./data saf-mcp
```

For MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector
```

Then connect to the local SAF server depending on your MCP host configuration.

## Example workflow

Put a CSV file in `data/`, for example `survey.csv`, then ask your MCP client:

> Inspect survey.csv, identify Likert variables, run Cronbach's alpha for Q1-Q5, and produce an APA report.

## Safety model

SAF only reads/writes inside `SAF_DATA_ROOT`. File paths are normalized and blocked if they try to escape the data root. Report/export writes require `SAF_ALLOW_WRITE=1`.

## SPSS compatibility philosophy

SAF should match SPSS conceptually where possible, but it should always disclose:

- method used
- library used
- assumptions checked
- rows removed because of missing values
- exact variables used
- p-value and effect size
- interpretation wording

## Suggested GitHub repo name

Recommended: `SAF`  
Long name: `Statistical-Analysis-Forge-MCP`
