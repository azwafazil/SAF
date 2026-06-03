from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from tabulate import tabulate

from .security import require_write_allowed


def p_value_text(p: float | None) -> str:
    if p is None:
        return "p = n/a"
    if p < 0.001:
        return "p < .001"
    return f"p = {p:.3f}"


def apa_interpretation(result: dict[str, Any]) -> str:
    method = result.get("method", "Statistical test")
    if "t" in result:
        return f"A {method} showed t({result.get('df', 'n/a'):.2f}) = {result['t']:.3f}, {p_value_text(result.get('p'))}."
    if "F" in result:
        return f"A {method} showed F = {result['F']:.3f}, {p_value_text(result.get('p'))}."
    if "chi2" in result:
        return f"A {method} showed χ²({result.get('df', 'n/a')}) = {result['chi2']:.3f}, {p_value_text(result.get('p'))}."
    if "alpha" in result:
        return f"The scale had Cronbach's α = {result['alpha']:.3f}, indicating {result.get('interpretation', 'internal consistency').lower()}."
    if "r_squared" in result:
        return f"The regression model explained {result['r_squared'] * 100:.1f}% of the variance, R² = {result['r_squared']:.3f}."
    return f"{method} completed."


def markdown_report(title: str, results: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    for i, result in enumerate(results, start=1):
        lines.append(f"## {i}. {result.get('method', 'Analysis')}")
        lines.append(apa_interpretation(result))
        lines.append("")
        if "tables" in result and isinstance(result["tables"], list):
            lines.append(tabulate(result["tables"], headers="keys", tablefmt="github"))
            lines.append("")
        elif "table" in result and isinstance(result["table"], list):
            lines.append(tabulate(result["table"], headers="keys", tablefmt="github"))
            lines.append("")
        elif "coefficients" in result:
            lines.append(tabulate(result["coefficients"], headers="keys", tablefmt="github"))
            lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def export_markdown_report(title: str, results: list[dict[str, Any]], output_file: str) -> dict[str, Any]:
    path = require_write_allowed(output_file)
    content = markdown_report(title, results)
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "output": str(path.name), "bytes": len(content.encode("utf-8"))}
