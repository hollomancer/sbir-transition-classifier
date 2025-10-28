"""CLI validate-config command for configuration validation."""

from pathlib import Path

import click
from loguru import logger

from ..config.schema import ConfigValidator


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to YAML configuration file to validate",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed validation information"
)
def validate_config(config: Path, verbose: bool):
    """Validate YAML configuration file for syntax and value errors."""

    if verbose:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="DEBUG")

    try:
        logger.info(f"Validating configuration file: {config}")

        # Run validation
        result = ConfigValidator.validate_file(config)

        # Display results
        summary = ConfigValidator.get_validation_summary(result)

        if result.valid:
            click.echo(f"✓ {summary}", color=True)

            if result.warnings and verbose:
                click.echo("\nWarnings:", err=True)
                for warning in result.warnings:
                    click.echo(f"  • {warning}", err=True)

            if verbose:
                click.echo(f"\nConfiguration file: {config}")
                click.echo("All validation checks passed.")
        else:
            click.echo(f"✗ {summary}", err=True, color=True)

            # Show errors and warnings
            error_details = ConfigValidator.format_errors_and_warnings(result)
            if error_details:
                click.echo(f"\n{error_details}", err=True)

            # Exit with error code
            raise click.ClickException("Configuration validation failed")

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise click.ClickException(f"Validation error: {e}")


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to YAML configuration file",
)
def check_config(config: Path):
    """Quick configuration check (alias for validate-config)."""
    # Import the validate_config function and call it
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(validate_config, ["--config", str(config)])

    if result.exit_code == 0:
        click.echo("Configuration is valid ✓")
    else:
        click.echo("Configuration has issues ✗", err=True)
        click.echo(result.output, err=True)
