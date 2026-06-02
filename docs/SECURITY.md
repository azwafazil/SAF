# Security

SAF is designed for privacy-first handling of SPSS-compatible datasets.

Security boundaries:

- All file reads and writes are resolved under `SAF_DATA_ROOT`.
- Path traversal outside `SAF_DATA_ROOT` is blocked.
- File extensions are validated before access.
- The server never executes shell commands.
- The server never executes SPSS syntax.
- The server never uploads or transmits datasets.

University survey files and research datasets may contain sensitive respondent data. Treat local data roots as private storage and avoid syncing them to public repositories.
