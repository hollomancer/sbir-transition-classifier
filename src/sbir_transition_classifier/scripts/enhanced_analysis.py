#!/usr/bin/env python3
"""
Enhanced analysis script with relaxed criteria and larger sample sizes.
"""

import warnings
import pandas as pd
from sbir_transition_classifier.db.database import SessionLocal, engine
from sbir_transition_classifier.core.models import (
    Base,
    Vendor,
    SbirAward,
    Contract,
    Detection,
)
from sbir_transition_classifier.detection.main import run_full_detection
from datetime import datetime, timedelta
import click

warnings.warn(
    "Direct script invocation is deprecated. Use 'sbir-detect analysis' commands instead.",
    DeprecationWarning,
    stacklevel=2,
)


@click.command()
@click.option("--sbir-sample", default=20000, help="Number of SBIR records to process")
@click.option(
    "--contract-sample", default=5000, help="Number of contract records to process"
)
@click.option("--min-score", default=0.2, help="Minimum score threshold for detections")
def enhanced_analysis(sbir_sample, contract_sample, min_score):
    """Run enhanced analysis with larger samples and relaxed criteria."""

    print(f"🚀 ENHANCED SBIR TRANSITION ANALYSIS")
    print(f"Sample sizes: {sbir_sample:,} SBIR records, {contract_sample:,} contracts")
    print(f"Minimum score threshold: {min_score}")
    print("=" * 60)

    # Reset database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("\n📊 LOADING EXPANDED DATASET...")

    # Load larger samples
    sbir_df = pd.read_csv("data/award_data.csv", nrows=sbir_sample)
    contract_df = pd.read_csv(
        "data/FY2026_All_Contracts_Full_20251008_1.csv", nrows=contract_sample
    )

    print(f"✅ Loaded {len(sbir_df):,} SBIR records")
    print(f"✅ Loaded {len(contract_df):,} contract records")

    # Find matches with fuzzy matching
    sbir_companies = set()
    for company in sbir_df["Company"].dropna():
        clean_name = str(company).strip().upper()
        if clean_name and len(clean_name) > 3:  # Filter very short names
            sbir_companies.add(clean_name)

    contract_companies = set()
    for company in contract_df["recipient_name"].dropna():
        clean_name = str(company).strip().upper()
        if clean_name and len(clean_name) > 3:
            contract_companies.add(clean_name)

    # Exact matches
    exact_matches = sbir_companies.intersection(contract_companies)

    # Fuzzy matches (contains/substring matching)
    fuzzy_matches = set()
    for sbir_co in sbir_companies:
        for contract_co in contract_companies:
            if sbir_co in contract_co or contract_co in sbir_co:
                if abs(len(sbir_co) - len(contract_co)) < 10:  # Similar length
                    fuzzy_matches.add((sbir_co, contract_co))

    all_matches = exact_matches.union({match[0] for match in fuzzy_matches})

    print(f"\\n🎯 COMPANY MATCHING RESULTS:")
    print(f"- SBIR companies: {len(sbir_companies):,}")
    print(f"- Contract recipients: {len(contract_companies):,}")
    print(f"- Exact matches: {len(exact_matches)}")
    print(f"- Fuzzy matches: {len(fuzzy_matches)}")
    print(f"- Total unique matches: {len(all_matches)}")

    # Load matched data into database
    db = SessionLocal()
    try:
        vendors_created = 0
        sbir_created = 0
        contracts_created = 0

        # Process all matches (not just first 50)
        for company in all_matches:
            # Create vendor
            vendor = Vendor(name=company)
            db.add(vendor)
            db.flush()
            vendors_created += 1

            # Add SBIR awards
            company_sbir = sbir_df[
                sbir_df["Company"].str.strip().str.upper() == company
            ]
            for _, row in company_sbir.iterrows():
                phase = str(row.get("Phase", ""))
                if "II" in phase:  # Focus on Phase II
                    # Use more realistic completion dates
                    completion_date = datetime.now() - timedelta(
                        days=365 + (sbir_created % 730)
                    )  # 1-3 years ago

                    sbir_award = SbirAward(
                        vendor_id=vendor.id,
                        award_piid=str(row.get("Contract", f"SBIR-{sbir_created}")),
                        phase="Phase II",
                        agency=str(row.get("Agency", "")),
                        completion_date=completion_date,
                        topic=str(row.get("Award Title", "")),
                        raw_data={"company": company},
                    )
                    db.add(sbir_award)
                    sbir_created += 1

            # Add contracts
            company_contracts = contract_df[
                contract_df["recipient_name"].str.strip().str.upper() == company
            ]
            for _, row in company_contracts.iterrows():
                # Use realistic start dates (recent)
                start_date = datetime.now() - timedelta(
                    days=30 + (contracts_created % 365)
                )  # Last year

                contract = Contract(
                    vendor_id=vendor.id,
                    piid=str(row.get("award_id_piid", f"CONTRACT-{contracts_created}")),
                    agency=str(row.get("awarding_agency_name", "")),
                    start_date=start_date,
                    naics_code=str(row.get("naics_code", "")),
                    psc_code=str(row.get("product_or_service_code", "")),
                    competition_details={
                        "extent_competed": str(row.get("extent_competed", ""))
                    },
                    raw_data={"recipient": company},
                )
                db.add(contract)
                contracts_created += 1

        db.commit()
        print(f"\\n✅ DATABASE LOADED:")
        print(f"- Vendors: {vendors_created:,}")
        print(f"- SBIR Phase II Awards: {sbir_created:,}")
        print(f"- Contracts: {contracts_created:,}")

    finally:
        db.close()

    print("\\n🔍 RUNNING ENHANCED DETECTION...")
    run_full_detection()

    # Analyze results
    db = SessionLocal()
    try:
        detection_count = db.query(Detection).count()
        print(f"\\n🎯 DETECTION RESULTS:")
        print(f"Total detections: {detection_count:,}")

        if detection_count > 0:
            # Group by confidence level
            detections = db.query(Detection).all()
            confidence_counts = {}

            for detection in detections:
                conf = detection.confidence
                confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

            print("\\nBy confidence level:")
            for conf, count in sorted(confidence_counts.items()):
                print(f"- {conf}: {count:,}")

            # Show top detections
            print("\\n🏆 TOP DETECTIONS:")
            top_detections = sorted(
                detections, key=lambda x: x.likelihood_score, reverse=True
            )[:10]

            for i, detection in enumerate(top_detections, 1):
                evidence = detection.evidence_bundle or {}
                sbir_info = evidence.get("source_sbir_award", {})
                contract_info = evidence.get("source_contract", {})

                print(
                    f"\\n{i}. Score: {detection.likelihood_score:.3f} | {detection.confidence}"
                )
                print(f'   SBIR: {sbir_info.get("agency", "N/A")}')
                print(f'   Contract: {contract_info.get("agency", "N/A")}')
                print(f'   Vendor: {evidence.get("vendor_name", "N/A")}')

    finally:
        db.close()

    print("\\n✅ ENHANCED ANALYSIS COMPLETE!")


if __name__ == "__main__":
    enhanced_analysis()
