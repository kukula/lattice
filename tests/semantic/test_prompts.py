"""Tests for semantic prompts."""

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.semantic.prompts import SYSTEM_PROMPT, build_analysis_prompt


class TestSystemPrompt:
    def test_system_prompt_exists(self):
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_issue_types(self):
        assert "CONTRADICTION" in SYSTEM_PROMPT
        assert "MISSING" in SYSTEM_PROMPT
        assert "AMBIGUOUS" in SYSTEM_PROMPT
        assert "EDGE_CASE" in SYSTEM_PROMPT

    def test_system_prompt_contains_format_instructions(self):
        assert "ISSUE:" in SYSTEM_PROMPT
        assert "CONTEXT:" in SYSTEM_PROMPT
        assert "DESCRIPTION:" in SYSTEM_PROMPT
        assert "NO_ISSUES_FOUND" in SYSTEM_PROMPT


class TestBuildAnalysisPrompt:
    def test_build_prompt_includes_yaml(self, minimal_model):
        prompt = build_analysis_prompt(minimal_model)

        assert "```yaml" in prompt
        assert "```" in prompt
        assert "entities:" in prompt

    def test_build_prompt_includes_entity_names(self, minimal_model):
        prompt = build_analysis_prompt(minimal_model)

        assert "User" in prompt
        assert "Post" in prompt

    def test_build_prompt_includes_attributes(self, minimal_model):
        prompt = build_analysis_prompt(minimal_model)

        assert "email" in prompt
        assert "title" in prompt

    def test_build_prompt_includes_states(self, stateful_model):
        prompt = build_analysis_prompt(stateful_model)

        assert "pending" in prompt
        assert "in_progress" in prompt
        assert "completed" in prompt

    def test_build_prompt_includes_transitions(self, stateful_model):
        prompt = build_analysis_prompt(stateful_model)

        assert "start" in prompt
        assert "complete" in prompt

    def test_build_prompt_asks_for_analysis(self, minimal_model):
        prompt = build_analysis_prompt(minimal_model)

        assert "analyze" in prompt.lower()
