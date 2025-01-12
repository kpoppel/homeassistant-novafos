# import pytest
import tests.utils


# @pytest.mark.skip(reason="Skipped")
def test_group_by_day(mocker, novafos):
    novafos._meter_data = tests.utils.load_data_structure("meter_data_small.json")

    expected = [
        ("2024-01-01", 0.168, 0.168, 0.168, 0.168, 0.168),
        ("2024-01-02", 0.67, 0.502, 0.168, 0.67, 0.419),
        ("2024-01-03", 0.289, -0.381, 0.289, 0.67, 0.48),
        ("2024-01-04", 0.232, -0.057, 0.232, 0.289, 0.261),
        ("2024-01-05", 0.117, -0.115, 0.117, 0.232, 0.175),
        ("2024-01-06", 0.155, 0.038, 0.117, 0.155, 0.136),
        ("2024-01-07", 0.17, 0.015, 0.155, 0.17, 0.163),
    ]

    assert novafos.group_by_day(meter_type="water") == expected
