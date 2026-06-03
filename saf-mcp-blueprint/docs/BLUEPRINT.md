# SAF MCP Blueprint

## 1. Product vision

SAF MCP should become a **student-friendly SPSS companion** first, then a partial SPSS alternative.

The correct positioning:

> SPSS = official classroom software.  
> SAF = auditable AI statistical assistant that can read/write SPSS files and explain outputs.

## 2. What to improve next

### Phase 1 — SPSS-like core reliability

Goal: make SAF useful for normal social-science assignments.

Must-have improvements:

1. Dataset registry
   - list files
   - validate file type
   - detect size
   - detect encoding
   - show row/column count

2. SPSS metadata preservation
   - variable labels
   - value labels
   - missing ranges
   - measure level: nominal / ordinal / scale
   - display widths and formats

3. Data dictionary generator
   - variable name
   - label
   - type
   - value labels
   - missing count
   - unique count
   - suggested measurement level

4. Analysis tools
   - descriptive statistics
   - frequencies
   - crosstab
   - chi-square
   - t-test
   - paired t-test
   - one-way ANOVA
   - repeated-measures ANOVA
   - correlation
   - linear regression
   - logistic regression
   - Cronbach's alpha
   - normality and Levene assumptions

5. Output layer
   - JSON output for agents
   - Markdown report for students
   - APA-style interpretation
   - SPSS-style table names

### Phase 2 — SPSS classroom compatibility

Goal: make SAF produce outputs that lecturers can understand.

1. SPSS syntax generator
   - DESCRIPTIVES
   - FREQUENCIES
   - CROSSTABS
   - T-TEST
   - ONEWAY
   - CORRELATIONS
   - REGRESSION
   - RELIABILITY

2. Output style presets
   - `style="spss"`
   - `style="apa7"`
   - `style="thesis"`
   - `style="beginner"`

3. Assignment helper
   - ask for research question
   - identify IV/DV
   - recommend test
   - explain why the test fits
   - produce null/alternative hypothesis

4. Table export
   - Markdown
   - CSV
   - XLSX
   - DOCX later if needed

### Phase 3 — Advanced social science research

1. Scale construction
   - reverse-coded items
   - subscale score creation
   - item-total correlation
   - alpha-if-item-deleted

2. Factor analysis
   - KMO
   - Bartlett's test
   - EFA extraction
   - rotation
   - loading table

3. Regression expansion
   - hierarchical regression
   - logistic regression
   - ordinal logistic regression
   - moderation
   - mediation

4. Survey cleaning
   - straight-lining detection
   - response duration screening
   - duplicate detection
   - careless response flag

### Phase 4 — SAF as MCP research OS

1. Recipes
   - JSON analysis recipe
   - reproducible pipeline
   - report generated from recipe

2. Audit ledger
   - file hash
   - variable list
   - test parameters
   - package versions
   - timestamp

3. Governance
   - no silent deletion
   - no external upload by default
   - no code execution from user dataset
   - privacy-first local analysis

4. MCP resources and prompts
   - dataset resource
   - data dictionary resource
   - `choose_test` prompt
   - `interpret_output` prompt

## 3. Architecture

```text
saf_mcp/
  server.py              MCP tool exposure
  config.py              environment settings
  security.py            safe path and write gates
  io.py                  CSV/XLSX/SAV readers and writers
  metadata.py            SPSS metadata and data dictionary
  audit.py               reproducibility records
  syntax.py              SPSS syntax generator
  reporting.py           Markdown/APA/SPSS-like output
  recipes.py             reproducible analysis pipeline
  stats/
    descriptive.py       descriptive, frequencies
    reliability.py       Cronbach alpha and scale diagnostics
    inferential.py       t-test, ANOVA, chi-square, correlation
    regression.py        OLS/logistic models
```

## 4. Statistical libraries

Recommended stack:

- pandas: data frame operations
- numpy: numerical operations
- scipy: core statistical tests
- statsmodels: regression and model summaries
- pingouin: t-test, ANOVA, correlation, effect size, reliability helpers
- pyreadstat: SPSS `.sav`, `.zsav`, `.por` read/write
- matplotlib: charts later

## 5. Tool design rules

Every SAF tool should return:

```json
{
  "ok": true,
  "method": "Independent samples t-test",
  "dataset": "survey.csv",
  "variables": ["gender", "score"],
  "n_used": 120,
  "n_dropped_missing": 4,
  "tables": [],
  "interpretation": "...",
  "warnings": [],
  "audit": {}
}
```

## 6. Non-negotiable safety rules

1. Dataset paths must stay inside `SAF_DATA_ROOT`.
2. Never execute commands embedded in data.
3. Never upload datasets externally unless explicitly implemented with consent.
4. Never overwrite original files without creating a new output file.
5. Every statistical result must include assumptions/warnings when relevant.
6. Every p-value must be reported with the test name and variables.

## 7. Roadmap priority

Best next build order:

1. Data dictionary + metadata preservation.
2. Analysis recipe runner.
3. APA interpretation generator.
4. SPSS syntax generator.
5. Report exporter.
6. Scale diagnostics.
7. Factor analysis.
8. Regression expansion.
9. MCP resources/prompts.
10. Secure remote deployment.
