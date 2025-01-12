from datetime import datetime
import random
import string
import requests


def test_login_using_access_token_too_short(novafos):
    access_token = "too_short"
    access_token_date_updated = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    assert (
        novafos.authenticate_using_access_token(access_token, access_token_date_updated)
        is False
    )


def test_login_using_access_token_out_of_date(novafos):
    rand = random.SystemRandom()
    access_token = "".join(rand.choices(string.ascii_letters + string.digits, k=1200))
    access_token_date_updated = datetime(2000, 1, 1).strftime("%Y-%m-%dT%H:%M:%S")
    assert (
        novafos.authenticate_using_access_token(access_token, access_token_date_updated)
        is False
    )


def test_login_using_access_token_ok(mocker, novafos):
    mock_get = mocker.patch("requests.get")
    mock_response = requests.Response()
    mock_response.status_code = 200
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
    """.encode()
    mock_post.return_value = mock_response

    rand = random.SystemRandom()
    access_token = "".join(rand.choices(string.ascii_letters + string.digits, k=1200))
    access_token_date_updated = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    assert (
        novafos.authenticate_using_access_token(access_token, access_token_date_updated)
        is True
    )
