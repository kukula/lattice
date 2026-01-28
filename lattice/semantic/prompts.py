"""Prompt templates for semantic validation."""

import yaml

from ..schema.models import LatticeModel

SYSTEM_PROMPT = """You are a system modeling expert analyzing Lattice models. Your task is to identify semantic issues that automated validators cannot detect.

Analyze the model for:
1. CONTRADICTION: Rules or constraints that conflict with each other
2. MISSING: Transitions, guards, or effects that should exist but don't
3. AMBIGUOUS: Unclear specifications that could be interpreted multiple ways
4. EDGE_CASE: Scenarios that aren't handled by the current model

Format your response EXACTLY as follows:

If you find issues:
---
ISSUE: [CONTRADICTION|MISSING|AMBIGUOUS|EDGE_CASE]
CONTEXT: [Entity.state] or [Entity] if no specific state
DESCRIPTION: A clear explanation of the issue
---

If the model is complete and has no issues:
NO_ISSUES_FOUND

Important:
- Focus on semantic gaps, not syntax or structural problems
- Consider real-world scenarios and edge cases
- Look for race conditions, timeouts, and error handling gaps
- Check if all paths have appropriate guards and effects
- Verify that invariants are enforceable and consistent
- Examine the 'unclear' sections if present - these are explicit ambiguities the author has noted"""


def build_analysis_prompt(model: LatticeModel) -> str:
    """Build the analysis prompt with the model content.

    Args:
        model: The LatticeModel to analyze.

    Returns:
        The prompt string including the serialized model.
    """
    # Convert model to a dictionary for YAML serialization
    model_dict = model.model_dump(exclude_none=True, by_alias=True)

    # Clean up empty lists and dicts for readability
    cleaned = _clean_model_dict(model_dict)

    model_yaml = yaml.dump(cleaned, default_flow_style=False, sort_keys=False)

    return f"""Please analyze this Lattice model for semantic issues:

```yaml
{model_yaml}```

Identify any contradictions, missing elements, ambiguities, or unhandled edge cases."""


def _clean_model_dict(data: dict) -> dict:
    """Remove empty lists and dicts for cleaner YAML output."""
    if not isinstance(data, dict):
        return data

    cleaned = {}
    for key, value in data.items():
        if isinstance(value, dict):
            cleaned_value = _clean_model_dict(value)
            if cleaned_value:  # Only include non-empty dicts
                cleaned[key] = cleaned_value
        elif isinstance(value, list):
            if value:  # Only include non-empty lists
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = _clean_model_dict(item)
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    else:
                        cleaned_list.append(item)
                if cleaned_list:
                    cleaned[key] = cleaned_list
        elif value is not None:
            cleaned[key] = value

    return cleaned
