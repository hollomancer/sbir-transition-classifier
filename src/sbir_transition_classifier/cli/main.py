"""Main CLI application for SBIR transition classifier."""

import click
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .run import run
from .bulk import bulk_process
from .validate import validate_config
from .reset import reset_config, list_templates, show_template
from .evidence import view_evidence, list_evidence, evidence_report
from .summary import generate_summary, quick_stats
from .hygiene import hygiene


@click.group()
@click.version_option(version="0.1.0", prog_name="sbir-detect")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(verbose: bool):
    """SBIR Transition Classifier - Local execution tool for detecting untagged SBIR Phase III transitions."""
    
    console = Console()
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    else:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="INFO")


# Add subcommands
main.add_command(run)
main.add_command(bulk_process, name="bulk-process")
main.add_command(validate_config, name="validate-config")
main.add_command(reset_config, name="reset-config")
main.add_command(list_templates, name="list-templates")
main.add_command(show_template, name="show-template")
main.add_command(view_evidence, name="view-evidence")
main.add_command(list_evidence, name="list-evidence")
main.add_command(evidence_report, name="evidence-report")
main.add_command(generate_summary, name="generate-summary")
main.add_command(quick_stats, name="quick-stats")
main.add_command(hygiene)


@main.command()
def version():
    """Show version information."""
    console = Console()
    console.print(Panel.fit(
        "[bold blue]SBIR Transition Classifier[/bold blue]\n"
        "[dim]Version 0.1.0[/dim]\n"
        "[dim]Local execution mode for SBIR Phase III transition detection[/dim]",
        border_style="blue"
    ))


@main.command()
def info():
    """Show system information and configuration."""
    import sys
    from pathlib import Path
    
    console = Console()
    
    # System info table
    info_table = Table(title="🖥️  System Information")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="white")
    
    info_table.add_row("Python Version", sys.version.split()[0])
    info_table.add_row("Platform", sys.platform)
    info_table.add_row("Working Directory", str(Path.cwd()))
    
    # Try to find default config
    try:
        from ..config.loader import ConfigLoader
        default_path = ConfigLoader.get_default_config_path()
        info_table.add_row("Default Config", str(default_path))
    except Exception as e:
        info_table.add_row("Default Config", f"[red]Not found ({e})[/red]")
    
    console.print(info_table)
    
    # Quick usage tips
    console.print()
    tips_table = Table(title="💡 Quick Start Tips")
    tips_table.add_column("Command", style="green")
    tips_table.add_column("Description", style="white")
    
    tips_table.add_row("sbir-detect bulk-process --verbose", "Run complete detection pipeline")
    tips_table.add_row("sbir-detect quick-stats", "Show database statistics")
    tips_table.add_row("sbir-detect --help", "Show all available commands")
    
    console.print(tips_table)


if __name__ == "__main__":
    main()
