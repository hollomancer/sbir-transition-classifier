"""Main CLI application for SBIR transition classifier."""

import click
from loguru import logger

from .run import run
from .validate import validate_config
from .reset import reset_config, list_templates, show_template
from .evidence import view_evidence, list_evidence, evidence_report
from .summary import generate_summary, quick_stats


@click.group()
@click.version_option(version="0.1.0", prog_name="sbir-detect")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(verbose: bool):
    """SBIR Transition Classifier - Local execution tool for detecting untagged SBIR Phase III transitions."""
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="DEBUG")
    else:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="INFO")


# Add subcommands
main.add_command(run)
main.add_command(validate_config, name="validate-config")
main.add_command(reset_config, name="reset-config")
main.add_command(list_templates, name="list-templates")
main.add_command(show_template, name="show-template")
main.add_command(view_evidence, name="view-evidence")
main.add_command(list_evidence, name="list-evidence")
main.add_command(evidence_report, name="evidence-report")
main.add_command(generate_summary, name="generate-summary")
main.add_command(quick_stats, name="quick-stats")


@main.command()
def version():
    """Show version information."""
    click.echo("SBIR Transition Classifier v0.1.0")
    click.echo("Local execution mode for SBIR Phase III transition detection")


@main.command()
def info():
    """Show system information and configuration."""
    import sys
    from pathlib import Path
    
    click.echo("System Information:")
    click.echo(f"  Python: {sys.version}")
    click.echo(f"  Platform: {sys.platform}")
    click.echo(f"  Working Directory: {Path.cwd()}")
    
    # Try to find default config
    try:
        from ..config.loader import ConfigLoader
        default_path = ConfigLoader.get_default_config_path()
        click.echo(f"  Default Config: {default_path}")
    except Exception as e:
        click.echo(f"  Default Config: Not found ({e})")


if __name__ == "__main__":
    main()
