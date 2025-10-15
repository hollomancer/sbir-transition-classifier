"""CLI reset-config command for configuration management."""

from pathlib import Path

import click
from loguru import logger

from ..config.reset import ConfigReset


@click.command()
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    required=True,
    help='Path where to write the configuration file'
)
@click.option(
    '--template', '-t',
    type=click.Choice(['default', 'high-precision', 'broad-discovery']),
    default='default',
    help='Configuration template to generate'
)
@click.option(
    '--overwrite',
    is_flag=True,
    help='Overwrite existing file if it exists'
)
@click.option(
    '--backup/--no-backup',
    default=True,
    help='Create backup of existing file (default: yes)'
)
def reset_config(output: Path, template: str, overwrite: bool, backup: bool):
    """Generate default or template configuration file."""
    
    try:
        # Check if file exists
        if output.exists() and not overwrite:
            click.echo(f"File already exists: {output}", err=True)
            click.echo("Use --overwrite to replace existing file", err=True)
            raise click.ClickException("File exists")
        
        # Generate configuration
        if template == 'default':
            success = ConfigReset.reset_to_default(output, backup_existing=backup)
        else:
            success = ConfigReset.generate_template(template, output, overwrite=overwrite)
        
        if success:
            click.echo(f"✓ Configuration written to: {output}")
            
            # Show template description
            description = ConfigReset.get_template_description(template)
            if description:
                click.echo(f"Template: {description}")
            
            # Show next steps
            click.echo("\nNext steps:")
            click.echo(f"  1. Review the configuration: cat {output}")
            click.echo(f"  2. Validate the configuration: sbir-detect validate-config --config {output}")
            click.echo(f"  3. Run detection: sbir-detect run --config {output} --output results/")
        else:
            raise click.ClickException("Failed to generate configuration")
    
    except Exception as e:
        logger.error(f"Reset config failed: {e}")
        raise click.ClickException(f"Configuration reset failed: {e}")


@click.command()
def list_templates():
    """List available configuration templates."""
    
    click.echo("Available configuration templates:")
    click.echo()
    
    templates = ConfigReset.list_available_templates()
    
    for template in templates:
        description = ConfigReset.get_template_description(template)
        click.echo(f"  {template:<15} - {description}")
    
    click.echo()
    click.echo("Usage:")
    click.echo("  sbir-detect reset-config --template <name> --output config/my-config.yaml")


@click.command()
@click.option(
    '--template', '-t',
    type=click.Choice(['default', 'high-precision', 'broad-discovery']),
    required=True,
    help='Template to show'
)
def show_template(template: str):
    """Show configuration template content."""
    
    try:
        from ..config.defaults import DefaultConfig
        import yaml
        
        if template == "default":
            config_dict = DefaultConfig.get_default_dict()
        elif template == "high-precision":
            config_dict = DefaultConfig.get_high_precision_template()
        elif template == "broad-discovery":
            config_dict = DefaultConfig.get_broad_discovery_template()
        else:
            raise ValueError(f"Unknown template: {template}")
        
        # Display template
        description = ConfigReset.get_template_description(template)
        click.echo(f"Template: {template}")
        click.echo(f"Description: {description}")
        click.echo("-" * 50)
        
        yaml_content = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
        click.echo(yaml_content)
        
    except Exception as e:
        logger.error(f"Show template failed: {e}")
        raise click.ClickException(f"Failed to show template: {e}")
