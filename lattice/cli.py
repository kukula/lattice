"""Command-line interface for Lattice."""

import sys

import click

from .output.formatter import format_validation_result
from .schema.errors import SchemaLoadError, SchemaValidationError
from .validators.runner import validate_model_file


def _get_semantic_analyzer():
    """Lazy import of semantic analyzer to avoid requiring anthropic."""
    try:
        from .semantic.analyzer import SemanticAnalyzer

        return SemanticAnalyzer
    except ImportError:
        return None


@click.group()
@click.version_option()
def main():
    """Lattice: A graph-based system modeling tool."""
    pass


@main.command()
@click.argument("model_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as errors",
)
def validate(model_file: str, output_format: str, strict: bool):
    """Validate a Lattice model file.

    MODEL_FILE is the path to a YAML model file.

    Exit codes:
      0 - Validation passed
      1 - Validation failed (errors found)
      2 - File or schema error
    """
    try:
        result = validate_model_file(model_file)
    except SchemaLoadError as e:
        click.echo(f"Error loading file: {e}", err=True)
        sys.exit(2)
    except SchemaValidationError as e:
        click.echo(f"Schema validation error: {e}", err=True)
        for err in e.errors:
            click.echo(f"  - {err['loc']}: {err['msg']}", err=True)
        sys.exit(2)

    # Output the result
    output = format_validation_result(result, output_format)  # type: ignore
    click.echo(output)

    # Determine exit code
    if result.has_errors:
        sys.exit(1)
    elif strict and result.has_warnings:
        sys.exit(1)
    else:
        sys.exit(0)


@main.command()
@click.argument("model_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--model",
    "claude_model",
    default="claude-sonnet-4-20250514",
    help="Claude model to use for analysis",
)
@click.option(
    "--include-structural/--no-include-structural",
    default=True,
    help="Run structural validation before semantic analysis",
)
def analyze(
    model_file: str,
    output_format: str,
    api_key: str | None,
    claude_model: str,
    include_structural: bool,
):
    """Perform semantic analysis on a Lattice model file.

    MODEL_FILE is the path to a YAML model file.

    This command uses Claude API to analyze the model for semantic issues
    like contradictions, missing elements, ambiguities, and edge cases.

    Exit codes:
      0 - Analysis passed (no errors)
      1 - Validation/analysis issues found
      2 - File, schema, or API error
    """
    from .graph.builder import build_graph
    from .schema.loader import parse_model
    from .semantic.errors import APIError, APIKeyMissingError
    from .validators.base import ValidationResult
    from .validators.runner import run_validators

    # Load the model
    try:
        model = parse_model(model_file)
        graph = build_graph(model)
    except SchemaLoadError as e:
        click.echo(f"Error loading file: {e}", err=True)
        sys.exit(2)
    except SchemaValidationError as e:
        click.echo(f"Schema validation error: {e}", err=True)
        for err in e.errors:
            click.echo(f"  - {err['loc']}: {err['msg']}", err=True)
        sys.exit(2)

    # Start with structural validation if requested
    result = ValidationResult()
    if include_structural:
        result = run_validators(model, graph)

    # Run semantic analysis
    try:
        SemanticAnalyzer = _get_semantic_analyzer()
        if SemanticAnalyzer is None:
            click.echo(
                "Error: The anthropic package is not installed.\n"
                "Install it with: pip install lattice[semantic]",
                err=True,
            )
            sys.exit(2)

        analyzer = SemanticAnalyzer(api_key=api_key, model=claude_model)
        semantic_result = analyzer.analyze(model)
        result.merge(semantic_result)

    except APIKeyMissingError as e:
        click.echo(f"API key error: {e}", err=True)
        sys.exit(2)
    except APIError as e:
        click.echo(f"API error: {e}", err=True)
        sys.exit(2)

    # Output the result
    output = format_validation_result(result, output_format)  # type: ignore
    click.echo(output)

    # Determine exit code
    if result.has_errors:
        sys.exit(1)
    else:
        sys.exit(0)


@main.command("generate-tests")
@click.argument("model_file", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    default="./tests/generated/",
    help="Output directory for generated test files",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "files"]),
    default="text",
    help="Output format: 'text' prints to stdout, 'files' writes to output-dir",
)
def generate_tests_cmd(model_file: str, output_dir: str, output_format: str):
    """Generate pytest stubs from a Lattice model.

    MODEL_FILE is the path to a YAML model file.

    Generates test stubs for:
    - State transitions (positive and negative)
    - Happy paths (initial → terminal)
    - Entity and system invariants

    Exit codes:
      0 - Success
      2 - File or schema error
    """
    from pathlib import Path

    from .test_generator import generate_tests_from_file
    from .test_generator.formatter import format_test_file, format_system_invariants_file
    from .test_generator.models import TestType

    try:
        result = generate_tests_from_file(model_file)
    except SchemaLoadError as e:
        click.echo(f"Error loading file: {e}", err=True)
        sys.exit(2)
    except SchemaValidationError as e:
        click.echo(f"Schema validation error: {e}", err=True)
        for err in e.errors:
            click.echo(f"  - {err['loc']}: {err['msg']}", err=True)
        sys.exit(2)

    if not result.files:
        click.echo("No tests to generate (model has no state machines or invariants)")
        sys.exit(0)

    if output_format == "text":
        # Print all generated code to stdout
        for test_file in result.files:
            click.echo(f"# {'=' * 70}")
            click.echo(f"# {test_file.filename}")
            click.echo(f"# {'=' * 70}")
            click.echo()

            # Use system invariants formatter for system file
            if test_file.entity == "system":
                system_tests = [
                    tc for tc in test_file.test_cases
                    if tc.test_type == TestType.SYSTEM_INVARIANT
                ]
                click.echo(format_system_invariants_file(system_tests))
            else:
                click.echo(format_test_file(test_file))

            click.echo()
    else:
        # Write files to output directory
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        for test_file in result.files:
            file_path = out_path / test_file.filename

            # Use system invariants formatter for system file
            if test_file.entity == "system":
                system_tests = [
                    tc for tc in test_file.test_cases
                    if tc.test_type == TestType.SYSTEM_INVARIANT
                ]
                content = format_system_invariants_file(system_tests)
            else:
                content = format_test_file(test_file)

            file_path.write_text(content)
            click.echo(f"Generated: {file_path}")

    click.echo(f"\nGenerated {result.total_tests} tests in {len(result.files)} files")
    sys.exit(0)


if __name__ == "__main__":
    main()
