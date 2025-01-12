# import pytest
import requests
import tests.utils


def prepare_active_meters(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = tests.utils.load_data(
        "active_meters_water_and_heating.json"
    )
    mock_post.return_value = mock_response
    novafos._get_active_meters()


# @pytest.mark.skip(reason="Need some data to test what is necessary here.")
def test_get_compsumption_timeseries(mocker, data_regression, novafos):
    prepare_active_meters(mocker, novafos)

    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = tests.utils.load_data(
        "consumption_hour_data_water_zoom_3.json"
    )
    mock_post.return_value = mock_response

    actuals = novafos._get_consumption_timeseries(
        novafos._active_meters[0], "2024-12-01", "2024-12-31"
    )
    data_regression.check(actuals)


# @pytest.mark.skip(reason="Need some data to test what is necessary here.")
def test_get_all_compsumption_timeseries(mocker, data_regression, novafos):
    prepare_active_meters(mocker, novafos)

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

    actuals = novafos._get_all_consumption_timeseries("2024-12-01", "2024-12-31", 3)
    data_regression.check(actuals)
