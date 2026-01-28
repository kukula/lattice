"""Output formatting for validation results."""

import json
from typing import Literal

from ..validators.base import Severity, ValidationResult


def format_validation_result(
    result: ValidationResult,
    format: Literal["text", "json"] = "text",
) -> str:
    """Format a validation result for output.

    Args:
        result: The validation result to format.
        format: Output format ("text" or "json").

    Returns:
        Formatted string representation.
    """
    if format == "json":
        return _format_json(result)
    return _format_text(result)


def _format_text(result: ValidationResult) -> str:
    """Format result as human-readable text."""
    lines: list[str] = []

    errors = result.errors
    warnings = result.warnings

    # Errors section
    lines.append("ERRORS:")
    if errors:
        for issue in errors:
            lines.append(f"  {_format_issue_text(issue)}")
    else:
        lines.append("  (none)")

    lines.append("")

    # Warnings section
    lines.append("WARNINGS:")
    if warnings:
        for issue in warnings:
            lines.append(f"  {_format_issue_text(issue)}")
    else:
        lines.append("  (none)")

    # Summary
    lines.append("")
    if result.is_valid:
        if warnings:
            lines.append(f"Validation passed with {len(warnings)} warning(s)")
        else:
            lines.append("Validation passed")
    else:
        lines.append(
            f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s)"
        )

    return "\n".join(lines)


def _format_issue_text(issue) -> str:
    """Format a single issue as text."""
    # Build location string
    location = ""
    if issue.entity:
        location = f"[{issue.entity}"
        if issue.state:
            location += f".{issue.state}"
        location += "] "

    # Severity symbol
    if issue.severity == Severity.ERROR:
        symbol = "✘"
    elif issue.severity == Severity.WARNING:
        symbol = "⚠"
    else:
        symbol = "ℹ"

    return f"{symbol} {issue.code}: {location}{issue.message}"


def _format_json(result: ValidationResult) -> str:
    """Format result as JSON."""
    data = {
        "valid": result.is_valid,
        "error_count": len(result.errors),
        "warning_count": len(result.warnings),
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "severity": issue.severity.value,
                "entity": issue.entity,
                "state": issue.state,
                "details": issue.details,
            }
            for issue in result.issues
        ],
    }
    return json.dumps(data, indent=2)
