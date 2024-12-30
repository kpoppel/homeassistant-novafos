import pytest
import requests
from . import utils

# Test cases:
# _get_hour_data(self, days_back = None, from_date = None)
#   1)  days_back = None
#       from_date = None
#       Requires _last_valid_day to be set correctly
#   2)  days_back = <integer>
#   3)  from_date = "<date in month>"
#
# Only "days_back=1" is ever used.

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

def test_get_hour_data_single(mocker, data_regression, novafos):
    prepare_active_meter(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = utils.load_data("consumption_hour_data_water_zoom_3.json")

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = utils.load_data("consumption_hour_data_heating_zoom_3.json")

    mock_post.side_effect = [mock_response_1, mock_response_2]

    novafos._last_valid_day = None

    novafos._get_hour_data(days_back=1)
    data_regression.check(novafos._meter_data)

def test_get_hour_data(mocker, data_regression, novafos):
    prepare_active_meters(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = utils.load_data("consumption_hour_data_water_zoom_3.json")

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = utils.load_data("consumption_hour_data_heating_zoom_3.json")

    mock_post.side_effect = [mock_response_1, mock_response_2]

    novafos._last_valid_day = None

    novafos._get_hour_data(days_back=1)
    data_regression.check(novafos._meter_data)
