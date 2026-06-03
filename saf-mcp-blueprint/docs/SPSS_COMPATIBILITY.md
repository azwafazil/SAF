# SPSS Compatibility Matrix

| SPSS workflow | SAF target | Status in scaffold |
|---|---|---|
| Open CSV | Read CSV | MVP |
| Open XLSX | Read XLSX | MVP |
| Open SAV | Read SAV via pyreadstat | MVP |
| Variable View | Data dictionary | MVP basic |
| Value labels | Metadata extraction | MVP basic |
| Missing values | Metadata + missing profile | Partial |
| Frequencies | Frequency table | MVP |
| Descriptives | Mean, SD, median, min, max | MVP |
| Crosstabs | Crosstab + chi-square | MVP basic |
| Compare Means | t-test / ANOVA | MVP |
| Correlate | Pearson/Spearman matrix | MVP |
| Regression | OLS | MVP basic |
| Reliability | Cronbach alpha | MVP basic |
| SPSS syntax | Generate syntax text | MVP basic |
| Output Viewer | Markdown/JSON report | MVP basic |
| AMOS / SEM | Not supported | Future / external package |

## Important limitation

SAF is not a legal or official replacement for IBM SPSS in a course where the lecturer explicitly requires IBM SPSS output.
