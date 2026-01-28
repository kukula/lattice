"""Response parsing for semantic validation."""

import re

from ..validators.base import Severity, ValidationIssue, ValidationResult

# Mapping from LLM issue types to validation codes
ISSUE_TYPE_CODES = {
    "CONTRADICTION": "SEMANTIC_CONTRADICTION",
    "MISSING": "SEMANTIC_MISSING",
    "AMBIGUOUS": "SEMANTIC_AMBIGUOUS",
    "EDGE_CASE": "SEMANTIC_EDGE_CASE",
}

# Pattern to match issue blocks
ISSUE_PATTERN = re.compile(
    r"ISSUE:\s*\[?(CONTRADICTION|MISSING|AMBIGUOUS|EDGE_CASE)\]?\s*\n"
    r"CONTEXT:\s*\[?([^\]\n]+)\]?\s*\n"
    r"DESCRIPTION:\s*(.+?)(?=\n---|\n\nISSUE:|\Z)",
    re.DOTALL | re.IGNORECASE,
)

# Pattern to extract entity and state from context like [Entity.state] or [Entity]
CONTEXT_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?$")


def parse_semantic_response(text: str) -> ValidationResult:
    """Parse the LLM response into a ValidationResult.

    Args:
        text: The raw LLM response text.

    Returns:
        A ValidationResult containing parsed issues as warnings.
    """
    result = ValidationResult()

    # Check for no issues response
    if "NO_ISSUES_FOUND" in text.upper():
        return result

    # Find all issue matches
    matches = ISSUE_PATTERN.findall(text)

    for match in matches:
        issue_type, context, description = match
        issue_type = issue_type.upper()

        # Get the validation code
        code = ISSUE_TYPE_CODES.get(issue_type, f"SEMANTIC_{issue_type}")

        # Parse entity and state from context
        entity, state = _parse_context(context.strip())

        # Clean up description
        description = description.strip()

        # Create the issue as a warning (semantic issues are less deterministic)
        issue = ValidationIssue(
            code=code,
            message=description,
            severity=Severity.WARNING,
            entity=entity,
            state=state,
        )
        result.add_issue(issue)

    return result


def _parse_context(context: str) -> tuple[str | None, str | None]:
    """Parse entity and state from context string.

    Args:
        context: Context string like "Entity.state" or "Entity" or "general"

    Returns:
        Tuple of (entity, state), either or both can be None.
    """
    # Remove brackets if present
    context = context.strip("[]")

    # Check for general/system-level context
    if context.lower() in ("general", "system", "global", "n/a", "none"):
        return None, None

    # Try to match Entity.state or Entity pattern
    match = CONTEXT_PATTERN.match(context)
    if match:
        entity = match.group(1)
        state = match.group(2)  # May be None
        return entity, state

    # If it doesn't match, it might be a general context
    return None, None
