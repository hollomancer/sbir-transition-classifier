import pytest
from datetime import datetime, timedelta
from sbir_transition_classifier.utils import dates
from sbir_transition_classifier.config.schema import ConfigSchema


@pytest.fixture
def mock_config():
    return ConfigSchema(
        detection={
            "timing": {
                "min_months_after_phase2": 1,
                "max_months_after_phase2": 24,
            }
        }
    )


def test_calculate_timing_window(mock_config):
    base_date = datetime(2022, 1, 1)
    start, end = dates.calculate_timing_window(base_date, mock_config)
    assert start == base_date + timedelta(days=30)
    assert end == base_date + timedelta(days=30 * 24)


@pytest.mark.parametrize(
    "piid, expected_year",
    [
        ("FA8650-20-C-5400", 2020),
        ("W911NF-21-C-0033", 2021),
        ("N68335-22-C-0100", 2022),
        ("12345-ABC-6789", None),
        ("NOYEAR", None),
        ("", None),
        (None, None),
    ],
)
def test_extract_year_from_piid(piid, expected_year):
    assert dates.extract_year_from_piid(piid) == expected_year


def test_has_date_mismatch():
    # Mismatch
    contract = {"piid": "FA8650-20-C-5400", "start_date": datetime(2023, 1, 1)}
    assert dates.has_date_mismatch(contract) is True

    # No mismatch
    contract = {"piid": "FA8650-20-C-5400", "start_date": datetime(2021, 1, 1)}
    assert dates.has_date_mismatch(contract) is False

    # No PIID year
    contract = {"piid": "NOYEAR", "start_date": datetime(2021, 1, 1)}
    assert dates.has_date_mismatch(contract) is False

    # No start date
    contract = {"piid": "FA8650-20-C-5400"}
    assert dates.has_date_mismatch(contract) is False


def test_get_months_between():
    date1 = datetime(2022, 1, 1)
    date2 = datetime(2022, 4, 1)
    assert dates.get_months_between(date1, date2) == 3.0

    date1 = datetime(2022, 1, 1)
    date2 = datetime(2021, 1, 1)
    assert dates.get_months_between(date1, date2) == -12.0


def test_is_within_timing_window(mock_config):
    award_date = datetime(2022, 1, 1)
    completion_date = datetime(2022, 1, 1)

    # Within window
    contract_date = completion_date + timedelta(days=60)
    assert (
        dates.is_within_timing_window(
            award_date, contract_date, mock_config, completion_date
        )
        is True
    )

    # Outside window (too early)
    contract_date = completion_date - timedelta(days=60)
    assert (
        dates.is_within_timing_window(
            award_date, contract_date, mock_config, completion_date
        )
        is False
    )

    # Outside window (too late)
    contract_date = completion_date + timedelta(days=30 * 25)
    assert (
        dates.is_within_timing_window(
            award_date, contract_date, mock_config, completion_date
        )
        is False
    )

    # No completion date
    contract_date = award_date + timedelta(days=60)
    assert dates.is_within_timing_window(award_date, contract_date, mock_config) is True
