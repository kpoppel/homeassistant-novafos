import pytest
import requests

def test_get_inactive_meters_water_and_heating(mocker, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = """
    [
        {
            "ConsumptionTypeId": 6,
            "InstallationId": 56781234,
            "IsActive": false,
            "MeasurementPointId": 66774455,
            "Units": [
                {
                    "Decimals": 0,
                    "Description": "Vand",
                    "Id": 32113,
                    "Name": "m³",
                    "Order": 1
                }
            ]
        },
        {
            "ConsumptionTypeId": 5,
            "InstallationId": 12345678,
            "IsActive": false,
            "MeasurementPointId": 44556677,
            "Units": [
                {
                    "Decimals": 0,
                    "Description": "Varme",
                    "Id": 11332,
                    "Name": "m³",
                    "Order": 1
                }
            ]
        }
    ]    
    """.encode('utf-8')
    mock_post.return_value = mock_response
    novafos._get_active_meters()

    assert novafos._active_meters == []
    # Depends on this being the first test to run
    assert novafos._meter_data == {}

def test_get_active_meters_water_ok(mocker, data_regression, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = """
    [
        {
            "ConsumptionTypeId": 6,
            "ConsumptionTypeName": "Vand",
            "InstallationId": 12345678,
            "InstallationPeriodId": 98765443,
            "InstallationPeriodPrintCode": 2,
            "IsActive": true,
            "IsChangedToRemoteReading": false,
            "IsRemoteRead": true,
            "Location": "Hus/Bryggers",
            "LocationId": 11223344,
            "MeasurementPointId": 44556677,
            "MeasurementPointNumber": "111122223333444455",
            "MeasurementPointResolution": "",
            "MeasurementPointType": "",
            "MeasurementPointTypeCodeText": "",
            "MeterId": 18018018,
            "MeterNumber": "44334433",
            "MeterTypeId": 16116116,
            "Units": [
                {
                    "Decimals": 0,
                    "Description": "Vand",
                    "Id": 11332,
                    "Name": "m³",
                    "Order": 1
                }
            ]
        }
    ]    
    """.encode('utf-8')
    mock_post.return_value = mock_response
    novafos._get_active_meters()
    # On first run create a yaml file with data from the data structure. Subsequently check against this file.
    data_regression.check(novafos._active_meters)

def test_get_active_meters_heating_ok(mocker, data_regression, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = """
    [
        {
            "ConsumptionTypeId": 5,
            "ConsumptionTypeName": "Varme",
            "InstallationId": 12345678,
            "InstallationPeriodId": 98765443,
            "InstallationPeriodPrintCode": 2,
            "IsActive": true,
            "IsChangedToRemoteReading": false,
            "IsRemoteRead": true,
            "Location": "Hus/Bryggers",
            "LocationId": 11223344,
            "MeasurementPointId": 44556677,
            "MeasurementPointNumber": "111122223333444455",
            "MeasurementPointResolution": "",
            "MeasurementPointType": "",
            "MeasurementPointTypeCodeText": "",
            "MeterId": 18018018,
            "MeterNumber": "44334433",
            "MeterTypeId": 16116116,
            "Units": [
                {
                    "Decimals": 0,
                    "Description": "Varme",
                    "Id": 11332,
                    "Name": "m³",
                    "Order": 1
                }
            ]
        }
    ]    
    """.encode('utf-8')
    mock_post.return_value = mock_response
    novafos._get_active_meters()
    # On first run create a yaml file with data from the data structure. Subsequently check against this file.
    data_regression.check(novafos._active_meters)

#@pytest.mark.skip(reason="Need some data to test what is necessary here.")
def test_get_active_meters_water_and_heating_ok(mocker, data_regression, novafos):
    mock_post = mocker.patch("requests.post")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = """
    [
        {
            "ConsumptionTypeId": 6,
            "InstallationId": 56781234,
            "IsActive": true,
            "MeasurementPointId": 66774455,
            "Units": [
                {
                    "Decimals": 0,
                    "Description": "Vand",
                    "Id": 32113,
                    "Name": "m³",
                    "Order": 1
                }
            ]
        },
        {
            "ConsumptionTypeId": 5,
            "InstallationId": 12345678,
            "IsActive": true,
            "MeasurementPointId": 44556677,
            "Units": [
                {
                    "Decimals": 0,
                    "Description": "Varme",
                    "Id": 11332,
                    "Name": "m³",
                    "Order": 1
                }
            ]
        }
    ]    
    """.encode('utf-8')
    mock_post.return_value = mock_response
    novafos._get_active_meters()
    # On first run create a yaml file with data from the data structure. Subsequently check against this file.
    data_regression.check(novafos._active_meters)

def test_get_meter_types(mocker, data_regression, novafos):
    novafos._active_meters = "Return me"
    assert novafos.get_meter_types() == "Return me"