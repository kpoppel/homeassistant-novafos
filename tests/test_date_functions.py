# import pytest
import datetime
import zoneinfo


# @pytest.mark.skip(reason="Skipped")
def test_local_to_utc(novafos):
    """Convert a local time to UTC time including timezone and summer(DST)/winter time offsets."""
    isostr = datetime.datetime.fromisoformat("2024-01-16T22:35:45")
    assert novafos._local_to_utc(isostr).tzinfo == zoneinfo.ZoneInfo("UTC")
    assert novafos._local_to_utc(isostr).isoformat() == "2024-01-16T21:35:45+00:00"


# @pytest.mark.skip(reason="Skipped")
def test_local_str_to_utc_str(novafos):
    """Convert a local ISO time string to UTC time strimg."""
    isodate = "2024-05-16T22:35:45"
    assert novafos._local_str_to_utc_str(isodate) == "2024-05-16T20:35:45Z"


# @pytest.mark.skip(reason="Skipped")
def test_local_str_to_utc(novafos):
    """Convert a local ISO time string to UTC time strimg."""
    isostr = "2023-06-12T23:34:56"
    assert novafos._local_str_to_utc(isostr).tzinfo == zoneinfo.ZoneInfo("UTC")
    assert novafos._local_str_to_utc(isostr).isoformat() == "2023-06-12T21:34:56+00:00"


def test_utc_to_isostr(novafos):
    """Convert a UTC time object to ISO time string."""
    utc_time = datetime.datetime(2014, 11, 22, 12, 38, 34, tzinfo=datetime.timezone.utc)
    assert novafos._utc_to_isostr(utc_time) == "2014-11-22T12:38:34Z"


def test_get_dummy_data(novafos):
    assert novafos.get_dummy_data() == {"water": [{"DateFrom": None, "Value": None}]}
