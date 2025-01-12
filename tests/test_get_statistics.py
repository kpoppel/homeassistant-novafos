import pytest
import requests
from datetime import datetime, timedelta
from . import utils

# Test cases:
# _get_statistics(self, days_back = None, from_date = None)
# get_statistics(self, from_date = None):
#   1)  from_date = None
#   3)  from_date = "<date in month>"

def prepare_active_meter(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = utils.load_data("active_meters_water.json")
    mock_post.return_value = mock_response
    novafos._get_active_meters()

def prepare_active_meters(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = utils.load_data("active_meters_water_and_heating.json")
    mock_post.return_value = mock_response
    novafos._get_active_meters()

# -----------------------------
#@pytest.mark.skip(reason="Skipped")
def test_get_statistics_single(mocker, data_regression, novafos):
    prepare_active_meter(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = utils.load_data("consumption_hour_data_water_zoom_3.json")

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = utils.load_data("consumption_hour_data_heating_zoom_3.json")

    mock_post.side_effect = [mock_response_1, mock_response_2]

    assert novafos.get_statistics(from_date=None) == None

#@pytest.mark.skip(reason="Skipped")
def test_statistics(mocker, data_regression, novafos) -> None:
    prepare_active_meter(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = utils.load_data("consumption_hour_data_water_zoom_3.json")

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = utils.load_data("consumption_hour_data_heating_zoom_3.json")

    mock_post.side_effect = [mock_response_1, mock_response_2]

    from_date = datetime.now()-timedelta(days=1)
    novafos.get_statistics(from_date=from_date)
    data_regression.check(novafos._meter_data)

