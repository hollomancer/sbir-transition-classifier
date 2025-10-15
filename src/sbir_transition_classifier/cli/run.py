"""CLI run command for local detection execution."""

import uuid
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from ..config.loader import ConfigLoader, ConfigLoadError
from ..config.validator import ConfigValidator
from ..data.models import DetectionSession, SessionStatus
from .output import OutputGenerator


@click.command()
@click.option(
    '--config', '-c',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to YAML configuration file'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    required=True,
    help='Output directory for results'
)
@click.option(
    '--data-dir',
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd() / "data",
    help='Directory containing input data files'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def run(config: Path, output: Path, data_dir: Path, verbose: bool):
    """Execute SBIR transition detection using specified configuration."""
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="DEBUG")
    
    try:
        # Validate configuration
        logger.info(f"Validating configuration: {config}")
        validation_result = ConfigValidator.validate_file(config)
        
        if not validation_result.valid:
            click.echo("Configuration validation failed:", err=True)
            click.echo(ConfigValidator.format_errors_and_warnings(validation_result), err=True)
            raise click.ClickException("Invalid configuration")
        
        if validation_result.warnings:
            click.echo("Configuration warnings:", err=True)
            for warning in validation_result.warnings:
                click.echo(f"  • {warning}", err=True)
        
        # Load configuration
        config_obj = ConfigLoader.load_from_file(config)
        logger.info("Configuration loaded successfully")
        
        # Create output directory
        output.mkdir(parents=True, exist_ok=True)
        
        # Create detection session
        session = DetectionSession(
            config_used=str(config.absolute()),
            config_checksum=_calculate_file_checksum(config),
            input_datasets=_find_input_datasets(data_dir),
            output_path=str(output.absolute())
        )
        
        logger.info(f"Starting detection session: {session.session_id}")
        
        # Import and run detection service
        from ..detection.pipeline import ConfigurableDetectionPipeline
        from ..data.local_loader import LocalDataLoader
        
        # Load data using local loader
        data_files = LocalDataLoader.discover_data_files(data_dir)
        
        sbir_awards = []
        contracts = []
        
        # Load SBIR awards
        for sbir_file in data_files['sbir_awards']:
            awards = LocalDataLoader.load_sbir_awards(sbir_file)
            sbir_awards.extend(awards)
        
        # Load contracts
        for contract_file in data_files['contracts']:
            contracts_data = LocalDataLoader.load_contracts(contract_file)
            contracts.extend(contracts_data)
        
        logger.info(f"Loaded {len(sbir_awards)} SBIR awards and {len(contracts)} contracts")
        
        # Run detection pipeline
        pipeline = ConfigurableDetectionPipeline(config_obj)
        
        # Validate input data
        validation_stats = pipeline.validate_input_data(sbir_awards, contracts)
        logger.info(f"Data validation: {validation_stats}")
        
        results = pipeline.run_detection(sbir_awards, contracts)
        
        # Generate output files
        output_gen = OutputGenerator(config_obj, session)
        output_files = output_gen.generate_outputs(results, output)
        
        # Update session status
        session.status = SessionStatus.COMPLETED
        session.detection_count = len(results)
        
        logger.info(f"Detection completed successfully. Found {len(results)} transitions.")
        
        click.echo(f"Detection completed successfully!")
        click.echo(f"Session ID: {session.session_id}")
        click.echo(f"Detections found: {len(results)}")
        click.echo(f"Output files:")
        for file_path in output_files:
            click.echo(f"  - {file_path}")
        
    except ConfigLoadError as e:
        logger.error(f"Configuration error: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise click.ClickException(f"Detection failed: {e}")


def _calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of file."""
    import hashlib
    
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def _find_input_datasets(data_dir: Path) -> list[str]:
    """Find input dataset files in data directory."""
    datasets = []
    
    # Look for common data file patterns
    patterns = ["*.csv", "*.json", "*.jsonl", "*.xlsx"]
    
    for pattern in patterns:
        for file_path in data_dir.glob(pattern):
            if file_path.is_file():
                datasets.append(str(file_path.absolute()))
    
    return datasets
