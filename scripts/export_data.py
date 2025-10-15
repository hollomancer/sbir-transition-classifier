import json
import click
import pandas as pd
from sqlalchemy.orm import Session
from sbir_transition_classifier.db.database import SessionLocal
from sbir_transition_classifier.core import models
from loguru import logger
import time
from pathlib import Path

@click.group()
def cli():
    pass

@cli.command()
@click.option('--output-path', default='detections.jsonl', help='Path to the output JSONL file.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def export_jsonl(output_path, verbose):
    """Exports all detections to a JSONL file."""
    if verbose:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="DEBUG")
    
    start_time = time.time()
    click.echo(f"📤 Exporting detections to {output_path}...")
    
    db: Session = SessionLocal()
    try:
        # Get count first for progress tracking
        total_count = db.query(models.Detection).count()
        
        if total_count == 0:
            click.echo("⚠️  No detections found in database.")
            return
        
        click.echo(f"🔍 Found {total_count:,} detections to export")
        
        detections = db.query(models.Detection).all()
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        exported_count = 0
        with open(output_path, 'w') as f:
            for i, detection in enumerate(detections, 1):
                try:
                    # A more complete implementation would serialize the full object
                    detection_data = {
                        'detection_id': str(detection.id),
                        'likelihood_score': detection.likelihood_score,
                        'confidence': detection.confidence,
                        'evidence_bundle': detection.evidence_bundle
                    }
                    f.write(json.dumps(detection_data) + '\n')
                    exported_count += 1
                    
                    # Progress indicator every 100 records or at the end
                    if i % 100 == 0 or i == total_count:
                        progress = (i / total_count) * 100
                        click.echo(f"📊 Progress: {i:,}/{total_count:,} ({progress:.1f}%)")
                        
                except Exception as e:
                    if verbose:
                        logger.warning(f"Error exporting detection {detection.id}: {e}")
                    continue
    
    finally:
        db.close()
    
    export_time = time.time() - start_time
    file_size = Path(output_path).stat().st_size / 1024  # KB
    
    click.echo(f"\n✅ Export complete!")
    click.echo(f"📈 Summary:")
    click.echo(f"   • Records exported: {exported_count:,}")
    click.echo(f"   • Output file: {output_path}")
    click.echo(f"   • File size: {file_size:.1f} KB")
    click.echo(f"   • Export time: {export_time:.1f} seconds")

@cli.command()
@click.option('--output-path', default='detections_summary.csv', help='Path to the output CSV file.')
def export_csv_summary(output_path):
    """Exports a CSV summary of all detections."""
    click.echo(f"Exporting detection summary to {output_path}...")
    db: Session = SessionLocal()
    try:
        # This query is simplified. A real implementation would need to join tables
        # to get vendor name, agency name, and fiscal year from the contract date.
        detections = db.query(models.Detection).all()
        
        # Create a pandas DataFrame for easier aggregation
        data = []
        for det in detections:
            data.append({
                'detection_id': str(det.id),
                'vendor_id': str(det.contract.vendor_id), # Placeholder
                'agency': det.contract.agency, # Placeholder
                'fiscal_year': det.contract.start_date.year, # Placeholder
                'score': det.likelihood_score
            })
        
        if not data:
            click.echo("No detections to export.")
            return

        df = pd.DataFrame(data)
        
        # In a real scenario, you would perform more complex aggregations here.
        summary_df = df.groupby(['fiscal_year', 'agency', 'vendor_id']).agg(
            detection_count=('detection_id', 'count'),
            average_score=('score', 'mean')
        ).reset_index()

        summary_df.to_csv(output_path, index=False)

    finally:
        db.close()
    click.echo("CSV summary export complete.")

if __name__ == '__main__':
    cli()

