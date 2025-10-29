import pytest
from sbir_transition_classifier.core.vendor_matching import VendorMatcher


@pytest.mark.parametrize(
    "input_name, expected_name",
    [
        ("ACME INC", "acme"),
        ("ACME Incorporated", "acme"),
        ("ACME LLC.", "acme"),
        ("ACME L.P.", "acme"),
        ("  ACME Company  ", "acme"),
        ("ACME", "acme"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_name(input_name, expected_name):
    assert VendorMatcher.normalize_name(input_name) == expected_name


@pytest.mark.parametrize(
    "name1, name2, expected_match",
    [
        ("ACME INC", "acme corporation", True),
        ("ACME LLC", "ACME Co.", True),
        ("ACME", "acme", True),
        ("ACME", "ACME INC", True),
        ("ACME", "ACME-X", False),
        ("ACME", "ACMEE", False),
        ("", "ACME", False),
        ("ACME", None, False),
    ],
)
def test_fuzzy_match(name1, name2, expected_match):
    assert VendorMatcher.fuzzy_match(name1, name2) == expected_match


def test_vendors_match():
    award = {"vendor_name": "ACME INC"}
    contract = {"vendor_name": "acme corporation"}
    assert VendorMatcher.vendors_match(award, contract) is True

    award = {"vendor_name": "ACME"}
    contract = {"vendor_name": "ACME-X"}
    assert VendorMatcher.vendors_match(award, contract) is False
