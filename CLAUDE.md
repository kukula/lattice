# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lattice is a graph-based system modeling tool for capturing and validating system intent. The core CLI is implemented with structural validation, semantic analysis (via Claude API), and test generation.

**Core Hypothesis:** A graph-based representation of system intent can be authored by humans, read/modified by LLMs, self-validate structurally, surface semantic gaps via LLM analysis, and generate meaningful tests from invariants.

## Architecture

```
Text Format (YAML) → Parse → Graph Storage (networkx)
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
    Structural Validation           Semantic Validation
       (fast, local)                  (async, LLM)
              ↓                               ↓
              └───────────────┬───────────────┘
                              ↓
                    Feedback Layer (errors/warnings)
                              ↓
                       Test Generation
```

## Model Structure

All models follow this YAML convention:

```yaml
entities:
  EntityName:
    attributes: [{name, type, constraints}]
    relationships: [belongs_to, has_many, has_one, depends_on]
    states: [for stateful entities]
    transitions: [{from, to, trigger, requires/guards, effects}]
    invariants: [constraints that must always hold]
    unclear: [explicit ambiguity markers for LLM analysis]

system_invariants: [cross-entity constraints]
temporal_rules: [time-based triggers]
```

## CLI Commands

```bash
intent validate model.yaml       # Structural validation
intent analyze model.yaml        # Semantic validation via LLM (requires ANTHROPIC_API_KEY)
intent generate-tests model.yaml # Generate pytest stubs
```

## Validation Categories

- **Structural (fast, local):** orphan detection, unreachable states, reference integrity, cycle detection, terminal state verification
- **Semantic (async, LLM):** contradiction detection, gap identification, ambiguity flagging, edge case discovery

## Demo Files

- `lattice-overview.md` - **The article** summarizing this project (4th in series)
- `demo-1-authorization.md` - Permission paths, role hierarchy, access control
- `demo-2-order-lifecycle.md` - E-commerce state machine, inventory tracking
- `demo-3-subscription-billing.md` - Temporal constraints, proration, plan transitions
- `implementation-experiment.md` - MVP architecture and milestones

## Tech Stack

- **Graph Storage:** Python dicts/networkx
- **Text Format:** YAML
- **Validation:** Python + networkx + Pydantic (structural), Claude API (semantic)
- **Test Output:** pytest stubs
- **CLI:** Click

## Project Structure

```
lattice/
├── cli.py              # CLI entry point (intent command)
├── schema/             # YAML parsing and Pydantic models
├── graph/              # Graph building and node types
├── validators/         # Structural validators (orphan, reachability, references)
├── semantic/           # LLM-based semantic analysis
├── test_generator/     # pytest stub generation
└── output/             # Result formatting (text/json)

examples/
├── minimal_valid.yaml
├── order_lifecycle.yaml
└── invalid/            # Models with intentional issues for testing
```
