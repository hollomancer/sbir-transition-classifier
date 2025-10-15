import json
import click
from sqlalchemy.orm import Session
from sbir_transition_classifier.db.database import SessionLocal
from sbir_transition_classifier.core import models

@click.group()
def cli():
    pass

@cli.command()
@click.option('--output-path', default='detections.jsonl', help='Path to the output JSONL file.')
def export_jsonl(output_path):
    """Exports all detections to a JSONL file."""
    click.echo(f"Exporting detections to {output_path}...")
    db: Session = SessionLocal()
    try:
        detections = db.query(models.Detection).all()
        with open(output_path, 'w') as f:
            for detection in detections:
                # A more complete implementation would serialize the full object
                f.write(json.dumps(detection.evidence_bundle) + '\n')
    finally:
        db.close()
    click.echo("Export complete.")

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

