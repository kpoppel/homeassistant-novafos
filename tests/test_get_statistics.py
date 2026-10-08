import pytest
import requests
from datetime import datetime, timedelta
from unittest.mock import Mock
from custom_components.novafos.pynovafos.novafos import Novafos
import tests.utils


# Test cases:
# _get_statistics(self, days_back = None, from_date = None)
# get_statistics(self, from_date = None):
#   1)  from_date = None
#   3)  from_date = "<date in month>"


def prepare_active_meter(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = tests.utils.load_data("active_meters_water.json")
    mock_post.return_value = mock_response
    novafos._get_active_meters()


def prepare_active_meters(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = tests.utils.load_data(
        "active_meters_water_and_heating.json"
    )
    mock_post.return_value = mock_response
    novafos._get_active_meters()


# -----------------------------
# @pytest.mark.skip(reason="Skipped")
def test_get_statistics_single(mocker, novafos):
    prepare_active_meter(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = tests.utils.load_data(
        "consumption_hour_data_water_zoom_3.json"
    )

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = tests.utils.load_data(
        "consumption_hour_data_heating_zoom_3.json"
    )

    mock_post.side_effect = [mock_response_1, mock_response_2]

    assert novafos.get_statistics(from_date=None) is None


# @pytest.mark.skip(reason="Skipped")
def test_statistics(mocker, data_regression, novafos) -> None:
    prepare_active_meter(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = tests.utils.load_data(
        "consumption_hour_data_water_zoom_3.json"
    )

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = tests.utils.load_data(
        "consumption_hour_data_heating_zoom_3.json"
    )

    mock_post.side_effect = [mock_response_1, mock_response_2]

    from_date = datetime.now() - timedelta(days=1)
    novafos.get_statistics(from_date=from_date)
    data_regression.check(novafos._meter_data)


@pytest.mark.parametrize(
    "meter_types", [("heating", "water"), ("water", "heating"), ("water",)]
)
def test_statistics_separates_meters_and_replaces_previous_fetch(meter_types, freezer):
    freezer.move_to("2026-10-08T12:00:00")
    api = Novafos(timezone="Europe/Copenhagen")
    api._meter_data = {meter_type: [] for meter_type in meter_types}
    api._meter_data_extra = {meter_type: [] for meter_type in meter_types}
    values = {"heating": 20.0, "water": 0.3}

    def time_series(dateFrom, dateTo, zoomLevel):
        return [
            {
                "type": meter_type,
                "Data": [{"DateFrom": dateFrom, "Value": values[meter_type]}],
                "Extra": {
                    "Sum": values[meter_type],
                    "Avg": values[meter_type],
                    "Max": values[meter_type],
                    "Min": values[meter_type],
                    "LastValidDate": dateTo,
                },
            }
            for meter_type in meter_types
        ]

    api._get_all_consumption_timeseries = Mock(side_effect=time_series)
    for from_date, expected_days in (
        (datetime(2026, 10, 5), 3),
        (datetime(2026, 10, 5), 3),
        (datetime(2026, 10, 7), 1),
        (datetime(2026, 10, 8), 0),
    ):
        data = api.get_statistics(from_date)
        for meter_type in meter_types:
            rows = data[meter_type]
            assert len(rows) == expected_days
            assert len({row["DateFrom"] for row in rows}) == expected_days
            assert [row["Value"] for row in rows] == [
                values[meter_type]
            ] * expected_days
            assert sum(row["Value"] for row in rows) == pytest.approx(
                expected_days * values[meter_type]
            )
            assert len(api._meter_data_extra[meter_type]) == expected_days
            assert all(
                extra["Sum"] == values[meter_type]
                for extra in api._meter_data_extra[meter_type]
            )
