# import pytest
import requests


def test_get_customer_id_ok(caplog, mocker, novafos):
    mock_get = mocker.patch("requests.get")
    mock_response = requests.Response()
    mock_response.status_code = 200
    # mock_response._content = b'{"key1": "value1", "key2": 123}'
    mock_response._content = b"""
    {
    "Customers": [
        {
            "City": "1000 MyTown",
            "ConsumptionTypes": [
                5,
                6
            ],
            "ContactInfos": [
                {
                    "Type": 1,
                    "Value": ""
                },
                {
                    "Type": 0,
                    "Value": "my@email.com"
                }
            ],
            "FullName": "John Doe",
            "Id": 12345678,
            "IsDefault": false,
            "Number": 1234567.8,
            "Roles": [
                "10"
            ],
            "StreetAddress": "Small Street 123"
        }
    ],
    "ProfileId": "abcdefff-0000-1234-9090-121212121212"
    }
    """
    mock_get.return_value = mock_response
    novafos._get_customer_id()

    # Search individual records
    # assert "Retrieved customer_id, number: 12345678, 1234567.8" in caplog.records[0].message
    # or searching in all output:
    # assert "Retrieved customer_id, number: 12345678, 1234567.8" in caplog.text

    # Or check the fields are set as required:
    assert novafos._customer_id == "12345678"
    assert novafos._customer_number == "1234567.8"


def test_get_customer_id_minimal_data_ok(caplog, mocker, novafos):
    mock_get = mocker.patch("requests.get")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = b"""
    {
    "Customers": [
        {
            "Id": 22345678,
            "Number": 1234567.8
        }
    ]
    }
    """
    mock_get.return_value = mock_response
    novafos._get_customer_id()
    # assert "Retrieved customer_id, number: 22345678, 1234567.8" in caplog.text
    assert novafos._customer_id == "22345678"
    assert novafos._customer_number == "1234567.8"


def test_get_customer_id_exception_on_no_id_field(caplog, mocker, novafos):
    mock_get = mocker.patch("requests.get")
    mock_response = requests.Response()
    mock_response.status_code = 200
    # Customer id does not contain the right fields
    mock_response._content = b"""
    {
    "Customers": [
        {
            "Number": 1234567.8
        }
    ]
    }
    """
    mock_get.return_value = mock_response
    try:
        novafos._get_customer_id()
        assert False
    except KeyError:
        assert True


def test_get_customer_id_exception_on_no_number_field(caplog, mocker, novafos):
    mock_get = mocker.patch("requests.get")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = b"""
    {
    "Customers": [
        {
            "Id": 12345678
        }
    ]
    }
    """
    mock_get.return_value = mock_response
    try:
        novafos._get_customer_id()
        assert False
    except KeyError:
        assert True
