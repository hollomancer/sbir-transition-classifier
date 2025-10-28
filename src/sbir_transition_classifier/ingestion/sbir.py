"""SBIR award data ingester."""

from collections import defaultdict
import time
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

from .base import BaseIngester, IngestionStats
from ..db import database as db_module
from ..core import models


class SbirIngester(BaseIngester):
    """Ingester for SBIR award CSV data."""

    def validate_file(self, file_path: Path) -> bool:
        """Validate SBIR CSV file structure."""
        try:
            df = pd.read_csv(file_path, nrows=5)
            # Check for core SBIR columns (flexible on award number field)
            required_cols = ["Company", "Phase", "Agency"]
            has_award_field = any(
                col in df.columns
                for col in ["Award Number", "Contract", "Agency Tracking Number"]
            )
            return all(col in df.columns for col in required_cols) and has_award_field
        except Exception:
            return False

    def ingest(self, file_path: Path, chunk_size: int = 20000) -> IngestionStats:
        """Ingest SBIR award data with complete loading and duplicate prevention."""
        start_time = time.time()

        if not self.validate_file(file_path):
            raise ValueError(f"Invalid SBIR file format: {file_path}")

        # Optimized CSV reading
        df = pd.read_csv(
            file_path, dtype=str, engine="c", na_filter=False, keep_default_na=False
        )

        self.stats.total_rows = len(df)
        self.log_progress(f"Loaded {self.stats.total_rows:,} rows from CSV")

        # Data validation and cleaning
        valid_df = self._clean_and_validate(df)

        # Bulk database operations with duplicate prevention
        db = db_module.SessionLocal()
        try:
            # Clear existing data to prevent duplicates from multiple loads
            existing_record = db.query(models.SbirAward.id).limit(1).first()
            if existing_record:
                self.log_progress(
                    "Existing SBIR awards detected - checking for duplicates"
                )

            self._bulk_insert_vendors(db, valid_df)
            inserted_count, duplicates_skipped = self._bulk_insert_awards_deduplicated(
                db, valid_df
            )
            db.commit()

            self.stats.valid_records = inserted_count
            self.stats.duplicates_skipped = duplicates_skipped
            if duplicates_skipped:
                self.stats.rejection_reasons["duplicates_skipped"] = duplicates_skipped

        finally:
            db.close()

        self.stats.processing_time = time.time() - start_time
        return self.stats

    def _clean_and_validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate SBIR data."""
        # Track rejections
        initial_count = len(df)

        # Remove missing company names
        missing_company = df["Company"].isna() | (df["Company"].str.strip() == "")
        self.stats.rejection_reasons["missing_company"] = missing_company.sum()
        df = df[~missing_company]

        # Date processing with fallbacks
        df["award_date"] = pd.to_datetime(df["Proposal Award Date"], errors="coerce")
        missing_dates = df["award_date"].isna()

        # Award Year fallback
        df.loc[missing_dates, "award_date"] = pd.to_datetime(
            df.loc[missing_dates, "Award Year"], format="%Y", errors="coerce"
        )

        # Track date fallbacks
        fallback_used = missing_dates & df["award_date"].notna()
        self.stats.rejection_reasons["date_fallbacks_used"] = fallback_used.sum()

        # Remove records with no valid dates
        still_missing = df["award_date"].isna()
        self.stats.rejection_reasons["missing_dates"] = still_missing.sum()
        df = df[~still_missing]

        self.stats.valid_records = len(df)
        self.stats.rejected_records = initial_count - self.stats.valid_records

        return df

    def _bulk_insert_vendors(self, db: Session, df: pd.DataFrame):
        """Bulk insert vendors."""
        vendor_names = df["Company"].str.strip().unique()
        existing_vendor_records = (
            db.query(models.Vendor).filter(models.Vendor.name.in_(vendor_names)).all()
        )
        existing_vendors = {v.name: v.id for v in existing_vendor_records}
        self._existing_vendor_ids = {v.id for v in existing_vendor_records}

        new_vendor_names = [
            name for name in vendor_names if name not in existing_vendors
        ]
        if new_vendor_names:
            new_vendors = [
                models.Vendor(name=name, created_at=pd.Timestamp.now())
                for name in new_vendor_names
            ]
            db.add_all(new_vendors)
            db.flush()

            for vendor in new_vendors:
                existing_vendors[vendor.name] = vendor.id

        # Store vendor mapping for awards
        self._vendor_map = existing_vendors

    def _load_existing_award_index(self, db: Session) -> dict:
        """Build an index of existing awards keyed by vendor for deduplication."""
        award_index = defaultdict(set)
        existing_vendor_ids = getattr(self, "_existing_vendor_ids", set())

        if not existing_vendor_ids:
            return award_index

        query = (
            db.query(
                models.SbirAward.vendor_id,
                models.SbirAward.award_piid,
                models.SbirAward.phase,
                models.SbirAward.agency,
            )
            .filter(models.SbirAward.vendor_id.in_(existing_vendor_ids))
            .yield_per(1000)
        )

        for vendor_id, piid, phase, agency in query:
            key = (
                str(piid or "").strip(),
                str(phase or "").strip(),
                str(agency or "").strip(),
            )
            award_index[vendor_id].add(key)

        self.log_progress(
            f"Prepared deduplication index for {len(award_index)} vendors"
        )
        return award_index

    def _bulk_insert_awards_deduplicated(
        self, db: Session, df: pd.DataFrame
    ) -> tuple[int, int]:
        """Bulk insert SBIR awards with duplicate prevention."""
        # Get existing awards to prevent duplicates
        existing_awards = self._load_existing_award_index(db)

        # Determine award number field (flexible for different CSV formats)
        award_field = None
        for field in ["Award Number", "Contract", "Agency Tracking Number"]:
            if field in df.columns:
                award_field = field
                break

        # Prepare new awards data with deduplication
        awards_data = []
        duplicates_skipped = 0

        for _, row in df.iterrows():
            company = row["Company"].strip()
            if company in self._vendor_map:
                vendor_id = self._vendor_map[company]
                award_piid = (
                    str(row.get(award_field, "")).strip() if award_field else ""
                )
                phase = str(row.get("Phase", "")).strip()
                agency = str(row.get("Agency", "")).strip()

                # Check for duplicate
                vendor_awards = existing_awards.setdefault(vendor_id, set())
                key = (award_piid, phase, agency)
                if key in vendor_awards:
                    duplicates_skipped += 1
                    continue

                # Add to existing set to prevent intra-batch duplicates
                vendor_awards.add(key)

                # Handle completion date properly (convert NaT to None)
                completion_date = pd.to_datetime(
                    row.get("Contract End Date"), errors="coerce"
                )
                if pd.isna(completion_date):
                    completion_date = None

                # Convert row to dict and ensure all values are JSON-serializable
                raw_data = row.to_dict()
                # Convert any Timestamp objects to ISO format strings
                for key, value in raw_data.items():
                    if isinstance(value, pd.Timestamp):
                        raw_data[key] = value.isoformat()

                awards_data.append(
                    {
                        "vendor_id": vendor_id,
                        "award_piid": award_piid,
                        "phase": phase,
                        "agency": agency,
                        "topic": str(row.get("Topic", "")),
                        "award_date": row["award_date"],
                        "completion_date": completion_date,
                        "raw_data": raw_data,
                        "created_at": pd.Timestamp.now(),
                    }
                )

        # Bulk insert new awards
        if awards_data:
            db.bulk_insert_mappings(models.SbirAward, awards_data)
            self.log_progress(
                f"Inserted {len(awards_data):,} new awards, skipped {duplicates_skipped:,} duplicates"
            )

        return len(awards_data), duplicates_skipped
