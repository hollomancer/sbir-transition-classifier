"""Vendor name matching and normalization utilities."""

from typing import Dict, Any, List


class VendorMatcher:
    """Handles vendor name matching and normalization."""

    # Common business suffixes to remove during normalization
    BUSINESS_SUFFIXES = [
        " inc",
        " inc.",
        " incorporated",
        " corp",
        " corp.",
        " corporation",
        " llc",
        " llc.",
        " l.l.c.",
        " ltd",
        " ltd.",
        " limited",
        " co",
        " co.",
        " company",
        " lp",
        " l.p.",
    ]

    @staticmethod
    def normalize_name(vendor_name: str) -> str:
        """
        Normalize vendor name for matching by removing common variations.

        Args:
            vendor_name: Raw vendor name

        Returns:
            Normalized vendor name (lowercase, trimmed, without suffixes)
        """
        if not vendor_name:
            return ""

        name_clean = vendor_name.lower().strip()

        # Remove common business suffixes
        for suffix in VendorMatcher.BUSINESS_SUFFIXES:
            if name_clean.endswith(suffix):
                name_clean = name_clean[: -len(suffix)].strip()

        # Remove extra whitespace
        name_clean = " ".join(name_clean.split())

        return name_clean

    @staticmethod
    def exact_match(name1: str, name2: str) -> bool:
        """
        Check if two vendor names match exactly (case-insensitive).

        Args:
            name1: First vendor name
            name2: Second vendor name

        Returns:
            True if names match exactly, False otherwise
        """
        if not name1 or not name2:
            return False

        return name1.lower().strip() == name2.lower().strip()

    @staticmethod
    def fuzzy_match(name1: str, name2: str) -> bool:
        """
        Check if two vendor names match after normalization.

        This handles common variations like:
        - "Acme Inc" vs "Acme Corporation"
        - "ABC LLC" vs "ABC Co."

        Args:
            name1: First vendor name
            name2: Second vendor name

        Returns:
            True if normalized names match, False otherwise
        """
        if not name1 or not name2:
            return False

        # Try exact match first (faster)
        if VendorMatcher.exact_match(name1, name2):
            return True

        # Normalize and compare
        norm1 = VendorMatcher.normalize_name(name1)
        norm2 = VendorMatcher.normalize_name(name2)

        return norm1 == norm2

    @staticmethod
    def vendors_match(award: Dict[str, Any], contract: Dict[str, Any]) -> bool:
        """
        Check if vendors match between award and contract.

        This is a convenience method that extracts vendor names and performs
        fuzzy matching. In production, this would be enhanced with proper
        vendor resolution using UEI, CAGE codes, DUNS numbers, etc.

        Args:
            award: SBIR award dictionary with 'vendor_name' key
            contract: Contract dictionary with 'vendor_name' key

        Returns:
            True if vendors match, False otherwise
        """
        award_vendor = str(award.get("vendor_name", ""))
        contract_vendor = str(contract.get("vendor_name", ""))

        return VendorMatcher.fuzzy_match(award_vendor, contract_vendor)

    @staticmethod
    def find_best_match(
        target_name: str, candidate_names: List[str]
    ) -> tuple[str | None, bool]:
        """
        Find the best matching vendor name from a list of candidates.

        Args:
            target_name: Target vendor name to match
            candidate_names: List of candidate vendor names

        Returns:
            Tuple of (best_match, is_exact) where:
                - best_match is the matching name (or None if no match)
                - is_exact indicates if it was an exact or fuzzy match
        """
        if not target_name or not candidate_names:
            return None, False

        # Try exact match first
        for candidate in candidate_names:
            if VendorMatcher.exact_match(target_name, candidate):
                return candidate, True

        # Try fuzzy match
        for candidate in candidate_names:
            if VendorMatcher.fuzzy_match(target_name, candidate):
                return candidate, False

        return None, False
