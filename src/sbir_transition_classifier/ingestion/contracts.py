"""Federal contract data ingester."""

import time
import uuid
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

from .base import BaseIngester, IngestionStats
from ..db import database as db_module
from ..core import models


class ContractIngester(BaseIngester):
    """Ingester for federal contract CSV data."""

    def validate_file(self, file_path: Path) -> bool:
        """Validate contract CSV file structure."""
        try:
            df = pd.read_csv(file_path, nrows=5)
            required_cols = ["award_id_piid", "awarding_agency_name", "recipient_name"]
            return all(col in df.columns for col in required_cols)
        except Exception:
            return False

    def ingest(self, file_path: Path, chunk_size: int = 100000) -> IngestionStats:
        """Ingest contract data with optimized chunked processing."""
        start_time = time.time()

        if not self.validate_file(file_path):
            raise ValueError(f"Invalid contract file format: {file_path}")

        # Required columns for performance
        required_cols = [
            "award_id_piid",
            "awarding_agency_name",
            "recipient_name",
            "modification_number",
            "transaction_number",
            "period_of_performance_start_date",
            "extent_competed",
            "type_of_contract_pricing",
        ]

        chunk_reader = pd.read_csv(
            file_path,
            chunksize=chunk_size,
            dtype=str,
            engine="c",
            na_filter=False,
            keep_default_na=False,
            usecols=required_cols,
        )

        db = db_module.SessionLocal()
        vendor_cache = {}

        try:
            for chunk_num, chunk_df in enumerate(chunk_reader, 1):
                self._process_chunk(db, chunk_df, vendor_cache, chunk_num)

        finally:
            db.close()

        self.stats.processing_time = time.time() - start_time
        return self.stats

    def _process_chunk(
        self, db: Session, chunk_df: pd.DataFrame, vendor_cache: dict, chunk_num: int
    ):
        """Process a single chunk of contract data."""
        chunk_start = len(chunk_df)
        self.stats.total_rows += chunk_start

        # Vectorized validation
        valid_mask = (
            chunk_df["award_id_piid"].notna()
            & (chunk_df["award_id_piid"].str.strip() != "")
            & chunk_df["awarding_agency_name"].notna()
            & (chunk_df["awarding_agency_name"].str.strip() != "")
        )

        # Track rejections
        missing_piid = (~chunk_df["award_id_piid"].notna()) | (
            chunk_df["award_id_piid"].str.strip() == ""
        )
        missing_agency = (~chunk_df["awarding_agency_name"].notna()) | (
            chunk_df["awarding_agency_name"].str.strip() == ""
        )

        self.stats.rejection_reasons["missing_piid"] = (
            self.stats.rejection_reasons.get("missing_piid", 0) + missing_piid.sum()
        )
        self.stats.rejection_reasons["missing_agency"] = (
            self.stats.rejection_reasons.get("missing_agency", 0) + missing_agency.sum()
        )

        chunk_df = chunk_df[valid_mask]

        if len(chunk_df) == 0:
            return

        # Bulk vendor processing
        self._process_vendors(db, chunk_df, vendor_cache)

        # Bulk contract insertion
        contracts_data = self._prepare_contracts(chunk_df, vendor_cache)
        if contracts_data:
            db.bulk_insert_mappings(models.Contract, contracts_data)
            db.commit()
            self.stats.valid_records += len(contracts_data)

        self.log_progress(
            f"Chunk {chunk_num}: {len(contracts_data):,} contracts inserted"
        )

    def _process_vendors(self, db: Session, chunk_df: pd.DataFrame, vendor_cache: dict):
        """Process vendors for the chunk."""
        recipients = chunk_df["recipient_name"].fillna("").str.strip()
        recipients = recipients[recipients != ""].unique()

        # Check existing vendors
        new_recipients = [name for name in recipients if name not in vendor_cache]
        if new_recipients:
            existing_vendors = (
                db.query(models.Vendor)
                .filter(models.Vendor.name.in_(new_recipients))
                .all()
            )

            for vendor in existing_vendors:
                vendor_cache[vendor.name] = vendor.id

            # Create new vendors
            still_new = [name for name in new_recipients if name not in vendor_cache]
            if still_new:
                new_vendors = [
                    models.Vendor(name=name, created_at=pd.Timestamp.now())
                    for name in still_new
                ]
                db.add_all(new_vendors)
                db.flush()

                for vendor in new_vendors:
                    vendor_cache[vendor.name] = vendor.id

    def _prepare_contracts(self, chunk_df: pd.DataFrame, vendor_cache: dict) -> list:
        """Prepare contract data for bulk insertion."""
        contracts_data = []

        # Vectorized PIID creation
        chunk_df["unique_piid"] = (
            chunk_df["award_id_piid"].astype(str)
            + "_"
            + chunk_df["modification_number"].fillna("0").astype(str)
            + "_"
            + chunk_df["transaction_number"].fillna("0").astype(str)
        )

        for _, row in chunk_df.iterrows():
            recipient = str(row.get("recipient_name", "")).strip()
            vendor_id = vendor_cache.get(recipient)

            contracts_data.append(
                {
                    "id": uuid.uuid4(),
                    "vendor_id": vendor_id,
                    "piid": row["unique_piid"],
                    "agency": row["awarding_agency_name"],
                    "start_date": pd.to_datetime(
                        row.get("period_of_performance_start_date"), errors="coerce"
                    ),
                    "competition_details": {
                        "extent_competed": str(row.get("extent_competed", "")),
                        "type_of_contract_pricing": str(
                            row.get("type_of_contract_pricing", "")
                        ),
                    },
                }
            )

        return contracts_data
