#!/usr/bin/env python3
"""
Reusable test data fixtures and factories.

This module provides factory functions for creating consistent test datasets
across integration and unit tests. It supports various scenarios including
happy paths, edge cases, and error conditions.
"""

from pathlib import Path
from datetime import datetime, timedelta
import csv
from typing import List, Dict, Any, Optional
import uuid


class SbirAwardFactory:
    """Factory for creating SBIR award test data."""

    @staticmethod
    def create_minimal(**overrides) -> Dict[str, Any]:
        """
        Create minimal valid SBIR award data.

        Args:
            **overrides: Fields to override in the default award

        Returns:
            Dictionary with SBIR award fields
        """
        defaults = {
            "Company": "Test Corporation",
            "Phase": "Phase II",
            "Agency": "Air Force",
            "Award Number": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "Proposal Award Date": "2022-01-01",
            "Contract End Date": "2022-12-31",
            "Award Title": "Test SBIR Award",
            "Program": "SBIR",
            "Topic": "Testing",
            "Award Year": "2022",
        }
        return {**defaults, **overrides}

    @staticmethod
    def create_with_vendor(vendor_name: str, **overrides) -> Dict[str, Any]:
        """Create award for specific vendor."""
        return SbirAwardFactory.create_minimal(Company=vendor_name, **overrides)

    @staticmethod
    def create_phase1(**overrides) -> Dict[str, Any]:
        """Create Phase I award."""
        return SbirAwardFactory.create_minimal(Phase="Phase I", **overrides)

    @staticmethod
    def create_phase2(**overrides) -> Dict[str, Any]:
        """Create Phase II award."""
        return SbirAwardFactory.create_minimal(Phase="Phase II", **overrides)

    @staticmethod
    def create_with_dates(
        award_date: str, completion_date: str, **overrides
    ) -> Dict[str, Any]:
        """Create award with specific dates."""
        year = award_date.split("-")[0]
        return SbirAwardFactory.create_minimal(
            **{
                "Proposal Award Date": award_date,
                "Contract End Date": completion_date,
                "Award Year": year,
                **overrides,
            }
        )

    @staticmethod
    def create_missing_dates(**overrides) -> Dict[str, Any]:
        """Create award with missing date fields (edge case)."""
        award = SbirAwardFactory.create_minimal(**overrides)
        award["Proposal Award Date"] = ""
        award["Contract End Date"] = ""
        return award

    @staticmethod
    def create_missing_company(**overrides) -> Dict[str, Any]:
        """Create award with missing company (should be rejected)."""
        award = SbirAwardFactory.create_minimal(**overrides)
        award["Company"] = ""
        return award


class ContractFactory:
    """Factory for creating contract test data."""

    @staticmethod
    def create_minimal(**overrides) -> Dict[str, Any]:
        """
        Create minimal valid contract data.

        Args:
            **overrides: Fields to override in the default contract

        Returns:
            Dictionary with contract fields
        """
        defaults = {
            "award_id_piid": f"CTR-{uuid.uuid4().hex[:8].upper()}",
            "awarding_agency_name": "Air Force",
            "recipient_name": "Test Corporation",
            "modification_number": "0",
            "transaction_number": "0",
            "period_of_performance_start_date": "2023-01-15",
            "extent_competed": "NOT COMPETED",
            "type_of_contract_pricing": "Firm-Fixed-Price",
        }
        return {**defaults, **overrides}

    @staticmethod
    def create_with_vendor(vendor_name: str, **overrides) -> Dict[str, Any]:
        """Create contract for specific vendor."""
        return ContractFactory.create_minimal(recipient_name=vendor_name, **overrides)

    @staticmethod
    def create_with_piid(piid: str, **overrides) -> Dict[str, Any]:
        """Create contract with specific PIID."""
        return ContractFactory.create_minimal(award_id_piid=piid, **overrides)

    @staticmethod
    def create_sole_source(**overrides) -> Dict[str, Any]:
        """Create sole-source (non-competed) contract."""
        return ContractFactory.create_minimal(
            extent_competed="NOT COMPETED", **overrides
        )

    @staticmethod
    def create_competed(**overrides) -> Dict[str, Any]:
        """Create competed contract."""
        return ContractFactory.create_minimal(
            extent_competed="FULL AND OPEN COMPETITION", **overrides
        )

    @staticmethod
    def create_with_start_date(start_date: str, **overrides) -> Dict[str, Any]:
        """Create contract with specific start date."""
        return ContractFactory.create_minimal(
            period_of_performance_start_date=start_date, **overrides
        )

    @staticmethod
    def create_missing_piid(**overrides) -> Dict[str, Any]:
        """Create contract with missing PIID (should be rejected)."""
        contract = ContractFactory.create_minimal(**overrides)
        contract["award_id_piid"] = ""
        return contract

    @staticmethod
    def create_missing_agency(**overrides) -> Dict[str, Any]:
        """Create contract with missing agency (should be rejected)."""
        contract = ContractFactory.create_minimal(**overrides)
        contract["awarding_agency_name"] = ""
        return contract


class DatasetFactory:
    """Factory for creating complete test datasets (awards + contracts)."""

    @staticmethod
    def create_small_happy_path() -> Dict[str, List[Dict[str, Any]]]:
        """
        Create small dataset with perfect matches.

        Returns:
            Dict with 'awards' and 'contracts' keys
        """
        vendor = "Acme Corporation"
        award_piid = "SBIR-001"
        completion_date = datetime(2022, 12, 31)
        start_date = completion_date + timedelta(days=30)

        awards = [
            SbirAwardFactory.create_with_dates(
                award_date="2022-01-01",
                completion_date=completion_date.strftime("%Y-%m-%d"),
                Company=vendor,
                **{"Award Number": award_piid},
            )
        ]

        contracts = [
            ContractFactory.create_with_piid(
                piid=award_piid,
                recipient_name=vendor,
                period_of_performance_start_date=start_date.strftime("%Y-%m-%d"),
                extent_competed="NOT COMPETED",
            )
        ]

        return {"awards": awards, "contracts": contracts}

    @staticmethod
    def create_edge_cases() -> Dict[str, List[Dict[str, Any]]]:
        """
        Create dataset with various edge cases.

        Returns:
            Dict with 'awards' and 'contracts' keys containing edge cases
        """
        awards = [
            # Valid award
            SbirAwardFactory.create_minimal(Company="EdgeCase Inc"),
            # Missing dates
            SbirAwardFactory.create_missing_dates(Company="NoDate Corp"),
            # Missing company (should reject)
            SbirAwardFactory.create_missing_company(
                **{"Award Number": "MISSING-VENDOR"}
            ),
            # Phase I (may be filtered out based on config)
            SbirAwardFactory.create_phase1(Company="Phase1 Corp"),
        ]

        contracts = [
            # Valid contract
            ContractFactory.create_minimal(recipient_name="EdgeCase Inc"),
            # Missing PIID (should reject)
            ContractFactory.create_missing_piid(recipient_name="NoData LLC"),
            # Missing agency (should reject)
            ContractFactory.create_missing_agency(recipient_name="NoAgency Inc"),
            # Competed contract
            ContractFactory.create_competed(recipient_name="EdgeCase Inc"),
        ]

        return {"awards": awards, "contracts": contracts}

    @staticmethod
    def create_detection_scenarios() -> Dict[str, Any]:
        """
        Create dataset with various detection scenarios.

        Returns:
            Dict with scenario metadata and data
        """
        vendor = "ScenarioTest Corp"
        base_completion = datetime(2022, 12, 31)

        scenarios = {
            "perfect_match": {
                "award": SbirAwardFactory.create_with_dates(
                    award_date="2022-01-01",
                    completion_date=base_completion.strftime("%Y-%m-%d"),
                    Company=vendor,
                    **{"Award Number": "PERFECT-001"},
                ),
                "contract": ContractFactory.create_with_piid(
                    piid="PERFECT-001",
                    recipient_name=vendor,
                    period_of_performance_start_date=(
                        base_completion + timedelta(days=30)
                    ).strftime("%Y-%m-%d"),
                    extent_competed="NOT COMPETED",
                    awarding_agency_name="Air Force",
                ),
                "expected_detection": True,
                "expected_score_range": (0.7, 1.0),
            },
            "late_contract": {
                "award": SbirAwardFactory.create_with_dates(
                    award_date="2022-01-01",
                    completion_date=base_completion.strftime("%Y-%m-%d"),
                    Company=vendor,
                    **{"Award Number": "LATE-001"},
                ),
                "contract": ContractFactory.create_with_start_date(
                    start_date=(base_completion + timedelta(days=300)).strftime(
                        "%Y-%m-%d"
                    ),
                    recipient_name=vendor,
                    award_id_piid="LATE-001",
                ),
                "expected_detection": False,  # Too late
                "expected_score_range": (0.0, 0.3),
            },
            "different_vendor": {
                "award": SbirAwardFactory.create_with_vendor(
                    "Company A", **{"Award Number": "DIFF-001"}
                ),
                "contract": ContractFactory.create_with_vendor(
                    "Company B", award_id_piid="DIFF-001"
                ),
                "expected_detection": False,  # Different vendors
                "expected_score_range": (0.0, 0.0),
            },
            "different_agency": {
                "award": SbirAwardFactory.create_minimal(
                    Company=vendor, Agency="Air Force", **{"Award Number": "AGENCY-001"}
                ),
                "contract": ContractFactory.create_with_piid(
                    piid="AGENCY-001",
                    recipient_name=vendor,
                    awarding_agency_name="Navy",
                ),
                "expected_detection": True,  # May still detect
                "expected_score_range": (0.3, 0.7),  # Lower score
            },
            "competed_vs_sole_source": {
                "award": SbirAwardFactory.create_minimal(
                    Company=vendor, **{"Award Number": "COMPETE-001"}
                ),
                "contracts": [
                    ContractFactory.create_sole_source(
                        recipient_name=vendor, award_id_piid="COMPETE-001"
                    ),
                    ContractFactory.create_competed(
                        recipient_name=vendor, award_id_piid="COMPETE-002"
                    ),
                ],
                "expected_note": "Sole source should score higher",
            },
        }

        return scenarios

    @staticmethod
    def create_medium_dataset(
        num_awards: int = 100, num_contracts: int = 500
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create medium-sized dataset for performance testing.

        Args:
            num_awards: Number of SBIR awards to generate
            num_contracts: Number of contracts to generate

        Returns:
            Dict with 'awards' and 'contracts' keys
        """
        awards = []
        for i in range(num_awards):
            vendor = f"Company_{i % 10}"  # 10 different vendors
            award = SbirAwardFactory.create_with_vendor(
                vendor, **{"Award Number": f"AWARD-{i:04d}"}
            )
            awards.append(award)

        contracts = []
        for i in range(num_contracts):
            vendor = f"Company_{i % 10}"
            contract = ContractFactory.create_with_vendor(
                vendor, award_id_piid=f"CONTRACT-{i:04d}"
            )
            contracts.append(contract)

        return {"awards": awards, "contracts": contracts}

    @staticmethod
    def create_duplicate_scenario() -> Dict[str, List[Dict[str, Any]]]:
        """
        Create dataset with duplicate awards (for testing deduplication).

        Returns:
            Dict with 'awards' containing duplicates
        """
        base_award = SbirAwardFactory.create_minimal(Company="DuplicateTest Inc")

        awards = [
            base_award.copy(),
            base_award.copy(),  # Exact duplicate
            {
                **base_award,
                "Award Title": "Different Title",
            },  # Same key fields, different title
        ]

        return {"awards": awards, "contracts": []}


def write_csv_dataset(
    path: Path, data: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None
) -> None:
    """
    Write dataset to CSV file.

    Args:
        path: Path to output CSV file
        data: List of dictionaries to write
        fieldnames: Column names (if None, uses keys from first dict)
    """
    if not data:
        # Empty dataset - write empty file
        path.touch()
        return

    if fieldnames is None:
        fieldnames = list(data[0].keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def write_sbir_csv(path: Path, awards: List[Dict[str, Any]]) -> None:
    """Write SBIR awards to CSV file."""
    fieldnames = [
        "Company",
        "Phase",
        "Agency",
        "Award Number",
        "Proposal Award Date",
        "Contract End Date",
        "Award Title",
        "Program",
        "Topic",
        "Award Year",
    ]
    write_csv_dataset(path, awards, fieldnames)


def write_contract_csv(path: Path, contracts: List[Dict[str, Any]]) -> None:
    """Write contracts to CSV file."""
    fieldnames = [
        "award_id_piid",
        "awarding_agency_name",
        "recipient_name",
        "modification_number",
        "transaction_number",
        "period_of_performance_start_date",
        "extent_competed",
        "type_of_contract_pricing",
    ]
    write_csv_dataset(path, contracts, fieldnames)


def setup_test_dataset(
    data_dir: Path, dataset_name: str = "small_happy_path"
) -> Dict[str, Path]:
    """
    Setup complete test dataset with CSV files.

    Args:
        data_dir: Directory to write CSV files
        dataset_name: Name of dataset to create (e.g., 'small_happy_path', 'edge_cases')

    Returns:
        Dict with paths to created files
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    if dataset_name == "small_happy_path":
        dataset = DatasetFactory.create_small_happy_path()
    elif dataset_name == "edge_cases":
        dataset = DatasetFactory.create_edge_cases()
    elif dataset_name == "medium":
        dataset = DatasetFactory.create_medium_dataset()
    elif dataset_name == "duplicates":
        dataset = DatasetFactory.create_duplicate_scenario()
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    award_file = data_dir / "award_data.csv"
    contract_file = data_dir / "contracts_1.csv"

    write_sbir_csv(award_file, dataset["awards"])
    write_contract_csv(contract_file, dataset.get("contracts", []))

    return {"awards": award_file, "contracts": contract_file}
