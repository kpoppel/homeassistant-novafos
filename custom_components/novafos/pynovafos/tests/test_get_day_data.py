import pytest
import requests
from . import utils

def prepare_active_meters(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = utils.load_data("active_meters_water_and_heating.json")
    mock_post.return_value = mock_response
    novafos._get_active_meters()

def test_get_day_data(mocker, data_regression, novafos):
    prepare_active_meters(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = utils.load_data("consumption_day_data_water_zoom_2.json")

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = utils.load_data("consumption_day_data_heating_zoom_2.json")

    mock_post.side_effect = [mock_response_1, mock_response_2]

    novafos._last_valid_day = None

    novafos._get_day_data()
    data_regression.check([novafos._last_valid_day, novafos._meter_data])

def test_get_day_data_invalid_date(mocker, data_regression, novafos):
    prepare_active_meters(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response_1 = requests.Response()
    mock_response_1.status_code = 200
    mock_response_1._content = utils.load_data("consumption_day_data_water_zoom_2.json")

    mock_response_2 = requests.Response()
    mock_response_2.status_code = 200
    mock_response_2._content = utils.load_data("consumption_day_data_heating_zoom_2.json")

    mock_post.side_effect = [mock_response_1, mock_response_2]

    # Check this date is overwritten
    novafos._last_valid_day = "I NEED TO BE OVERWRITTEN"

    novafos._get_day_data()
    data_regression.check([novafos._last_valid_day, novafos._meter_data])
    