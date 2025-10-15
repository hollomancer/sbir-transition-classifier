import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import dask.dataframe as dd
import click
from sqlalchemy.orm import Session
from src.sbir_transition_classifier.db.database import SessionLocal, engine
from src.sbir_transition_classifier.core import models

def init_db():
    models.Base.metadata.create_all(bind=engine)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--file-path', default='data/award_data.csv', help='Path to the SBIR award data CSV file.')
@click.option('--chunk-size', default=10000, help='Number of rows to process at a time.')
def load_sbir_data(file_path, chunk_size):
    """Loads SBIR award data from a CSV file into the database."""
    click.echo("Initializing database...")
    init_db()
    click.echo(f"Loading SBIR data from {file_path}...")

    # Use Dask for potentially large files
    ddf = dd.read_csv(file_path)

    db: Session = SessionLocal()
    try:
        # This is a simplified example. A real implementation would need to handle
        # vendor creation and linking more robustly.
        # It assumes a 'Company' and other relevant columns exist.
        for partition in ddf.partitions:
            df = partition.compute()
            for _, row in df.iterrows():
                # Basic data cleaning and vendor handling
                company_name = row.get('Company')
                if not company_name:
                    continue

                vendor = db.query(models.Vendor).filter(models.Vendor.name == company_name).first()
                if not vendor:
                    vendor = models.Vendor(name=company_name)
                    db.add(vendor)
                    db.commit()

                award = models.SbirAward(
                    vendor_id=vendor.id,
                    award_piid=row.get('Award Number'),
                    phase=row.get('Phase'),
                    agency=row.get('Agency'),
                    # Add robust date parsing
                    # award_date=pd.to_datetime(row.get('Award Date'), errors='coerce'),
                    # completion_date=pd.to_datetime(row.get('End Date'), errors='coerce'),
                    topic=row.get('Topic'),
                )
                db.add(award)
            db.commit()
            click.echo(f"Committed a chunk of {len(df)} records.")

    finally:
        db.close()

    click.echo("Finished loading SBIR data.")

@cli.command()
def load_usaspending_data():
    """Placeholder for loading USAspending data."""
    click.echo("USAspending data loading is not yet implemented.")

if __name__ == '__main__':
    cli()
