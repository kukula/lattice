# Contributing to Lattice

Thank you for your interest in contributing to Lattice! This document provides guidelines and instructions for contributing.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/tolik/lattice.git
   cd lattice
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install in development mode with all dependencies:
   ```bash
   pip install -e ".[dev,semantic]"
   ```

   - `dev` includes testing dependencies (pytest, etc.)
   - `semantic` includes Claude API integration (anthropic SDK)

4. Set up your API key for semantic analysis (optional):
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   ```

## Running Tests

Run the full test suite:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest tests/test_validators.py
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where practical
- Keep functions focused and single-purpose
- Write docstrings for public APIs

## Pull Request Workflow

1. **Fork** the repository and create your branch from `main`
2. **Make your changes** with clear, focused commits
3. **Add tests** for any new functionality
4. **Run the test suite** to ensure nothing is broken
5. **Update documentation** if you're changing behavior
6. **Submit a PR** with a clear description of your changes

### PR Guidelines

- Keep PRs focused on a single feature or fix
- Include a clear description of what and why
- Reference any related issues
- Ensure all tests pass before requesting review

## Reporting Issues

When reporting bugs, please include:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant YAML model files (if applicable)

## Questions?

Feel free to open an issue for questions or discussions about potential contributions.
