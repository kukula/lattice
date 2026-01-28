# Lattice: Graph-Based System Intent Modeling

We've established that code is a lossy format, proposed the self-validating graph as a solution, and outlined an incremental adoption path. Now let's look at Lattice—a tool that puts these ideas into practice. Here's what modeling, validating, and generating tests actually looks like.

**Repository:** [github.com/kukula/lattice](https://github.com/kukula/lattice)

## The Core Idea

Lattice represents system behavior as a graph. Entities, their states, relationships, and transitions form nodes and edges that can be traversed, queried, and validated. The format is flexible—these demos use YAML, but any structured format works:

```yaml
entities:
  User:
    attributes:
      - name: email
        type: string
        unique: true
    relationships:
      - has_many: Post

  Post:
    belongs_to: User
    attributes:
      - name: title
        type: string

    states:
      - name: draft
        initial: true
      - name: published
        terminal: true

    transitions:
      - from: draft
        to: published
        trigger: user.publish
```

This graph-based approach makes intent machine-readable without sacrificing human authorship. The structure is rigid enough for automated analysis yet expressive enough to capture real-world complexity.

## What Lattice Does

Lattice performs two types of validation. **Structural validation** runs fast and locally—detecting orphaned entities, unreachable states, broken references, and cycles. Consider a model with issues:

```yaml
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: in_progress
      - name: completed
        terminal: true
      - name: secret  # No incoming transitions!

    transitions:
      - from: pending
        to: in_progress
        trigger: user.start
      - from: in_progress
        to: completed
        trigger: user.complete
      - from: secret  # Can never reach this state
        to: completed
        trigger: admin.resolve
```

Lattice catches this immediately:

```
$ intent validate task_model.yaml
ERRORS:
  ✘ UNREACHABLE_STATE: [Task.secret] State 'secret' cannot be reached from initial state 'pending'

WARNINGS:
  (none)

Validation failed: 1 error(s), 0 warning(s)
```

**Semantic validation** leverages LLM analysis to find contradictions that structural rules miss. Given an authorization model with these rules:

```yaml
authorization_rules:
  - name: owner_access
    rule: "user == resource.owner => allow(*)"

  - name: suspended_block
    rule: "user.status == suspended => deny(*)"
    priority: high
```

The LLM surfaces the conflict:

```
$ intent analyze auth_model.yaml
ERRORS:
  (none)

WARNINGS:
  ⚠ SEMANTIC_CONTRADICTION: [Resource] Rule 'owner_access' grants owner full access,
    but 'suspended_block' denies all actions for suspended users. If owner is
    suspended, which rule wins? Consider adding explicit priority or a
    'suspended_owner' rule.

Validation passed with 1 warning(s)
```

## Test Generation

From validated models, Lattice generates test stubs. State transitions become test scenarios:

```python
class TestPositiveTransitions:
    """Tests for valid state transitions."""

    def test_post_draft_to_published(self, post_in_draft_state):
        """
        Post transitions from draft to published on user.publish
        """
        # Trigger: user.publish
        # TODO: Assert state == 'published'
        pass
```

```
$ intent generate-tests examples/minimal_valid.yaml
Generated 5 tests in 1 files
```

## Practical Applications

The approach applies wherever complex rules govern behavior: authorization systems with role hierarchies, e-commerce workflows with order states, subscription billing with temporal rules.

## Why It Matters

Lattice bridges the gap between documentation and implementation. Intent becomes verifiable, assumptions become explicit, and the model serves as a living specification.
