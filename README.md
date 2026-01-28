# Lattice

A graph-based system modeling tool for capturing and validating system intent.

**Read the full overview:** [lattice-overview.md](lattice-overview.md)

## License

MIT - see [LICENSE](LICENSE)

## Installation

```bash
pip install -e .

# For semantic analysis (requires Anthropic API key)
pip install -e ".[semantic]"
```

## Quick Start

Validate a model:

```bash
intent validate examples/minimal_valid.yaml
```

Generate test stubs:

```bash
intent generate-tests examples/minimal_valid.yaml
```

Run semantic analysis (requires `ANTHROPIC_API_KEY`):

```bash
intent analyze examples/minimal_valid.yaml
```

## What It Does

- **Structural validation** - Detects orphan entities, unreachable states, broken references
- **Semantic validation** - LLM-based contradiction and gap detection
- **Test generation** - Generates pytest stubs from state transitions

## Example Model

```yaml
entities:
  Post:
    belongs_to: User
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
