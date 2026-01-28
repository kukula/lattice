"""Tests for semantic response parser."""

import pytest

from lattice.semantic.parser import parse_semantic_response
from lattice.validators.base import Severity


class TestParseNoIssues:
    def test_no_issues_found_returns_empty_result(self):
        response = "NO_ISSUES_FOUND"
        result = parse_semantic_response(response)

        assert len(result.issues) == 0
        assert result.is_valid

    def test_no_issues_found_case_insensitive(self):
        response = "no_issues_found"
        result = parse_semantic_response(response)

        assert len(result.issues) == 0

    def test_no_issues_found_with_surrounding_text(self):
        response = """After careful analysis of the model, I found:

NO_ISSUES_FOUND

The model appears complete and well-structured."""
        result = parse_semantic_response(response)

        assert len(result.issues) == 0


class TestParseSingleIssue:
    def test_parse_contradiction_issue(self):
        response = """---
ISSUE: CONTRADICTION
CONTEXT: [Order.pending]
DESCRIPTION: The state allows both cancellation and payment simultaneously
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.code == "SEMANTIC_CONTRADICTION"
        assert issue.entity == "Order"
        assert issue.state == "pending"
        assert "cancellation" in issue.message
        assert issue.severity == Severity.WARNING

    def test_parse_missing_issue(self):
        response = """---
ISSUE: MISSING
CONTEXT: [Order]
DESCRIPTION: No transition handles payment timeout
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.code == "SEMANTIC_MISSING"
        assert issue.entity == "Order"
        assert issue.state is None
        assert "timeout" in issue.message

    def test_parse_ambiguous_issue(self):
        response = """---
ISSUE: AMBIGUOUS
CONTEXT: [Shipment]
DESCRIPTION: States defined but unclear how they relate to Order states
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.code == "SEMANTIC_AMBIGUOUS"
        assert issue.entity == "Shipment"

    def test_parse_edge_case_issue(self):
        response = """---
ISSUE: EDGE_CASE
CONTEXT: [Order.cancelled]
DESCRIPTION: What if refund fails after cancellation?
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.code == "SEMANTIC_EDGE_CASE"
        assert issue.entity == "Order"
        assert issue.state == "cancelled"


class TestParseMultipleIssues:
    def test_parse_multiple_issues(self):
        response = """---
ISSUE: MISSING
CONTEXT: [Order]
DESCRIPTION: No timeout handling for payment_pending state
---

---
ISSUE: EDGE_CASE
CONTEXT: [Order.cancelled]
DESCRIPTION: Refund failure scenario not addressed
---

---
ISSUE: AMBIGUOUS
CONTEXT: [Shipment]
DESCRIPTION: Link to Order state machine unclear
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 3

        codes = [i.code for i in result.issues]
        assert "SEMANTIC_MISSING" in codes
        assert "SEMANTIC_EDGE_CASE" in codes
        assert "SEMANTIC_AMBIGUOUS" in codes


class TestParseContextFormats:
    def test_entity_with_state(self):
        response = """---
ISSUE: MISSING
CONTEXT: [Order.payment_pending]
DESCRIPTION: Test
---"""
        result = parse_semantic_response(response)

        issue = result.issues[0]
        assert issue.entity == "Order"
        assert issue.state == "payment_pending"

    def test_entity_without_state(self):
        response = """---
ISSUE: MISSING
CONTEXT: [Customer]
DESCRIPTION: Test
---"""
        result = parse_semantic_response(response)

        issue = result.issues[0]
        assert issue.entity == "Customer"
        assert issue.state is None

    def test_context_without_brackets(self):
        response = """---
ISSUE: MISSING
CONTEXT: Order.submitted
DESCRIPTION: Test
---"""
        result = parse_semantic_response(response)

        issue = result.issues[0]
        assert issue.entity == "Order"
        assert issue.state == "submitted"

    def test_general_context(self):
        response = """---
ISSUE: CONTRADICTION
CONTEXT: general
DESCRIPTION: System-wide invariants conflict
---"""
        result = parse_semantic_response(response)

        issue = result.issues[0]
        assert issue.entity is None
        assert issue.state is None


class TestParseEdgeCases:
    def test_multiline_description(self):
        response = """---
ISSUE: EDGE_CASE
CONTEXT: [Order]
DESCRIPTION: When a customer cancels during payment processing,
the payment gateway might still complete the charge.
This race condition needs handling.
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 1
        assert "race condition" in result.issues[0].message

    def test_issue_type_case_insensitive(self):
        response = """---
ISSUE: missing
CONTEXT: [Order]
DESCRIPTION: Test
---"""
        result = parse_semantic_response(response)

        assert len(result.issues) == 1
        assert result.issues[0].code == "SEMANTIC_MISSING"

    def test_empty_response(self):
        response = ""
        result = parse_semantic_response(response)

        assert len(result.issues) == 0

    def test_issues_are_warnings(self):
        response = """---
ISSUE: CONTRADICTION
CONTEXT: [Order]
DESCRIPTION: Test contradiction
---"""
        result = parse_semantic_response(response)

        # All semantic issues should be warnings, not errors
        assert all(i.severity == Severity.WARNING for i in result.issues)
        assert result.is_valid  # No errors means valid
