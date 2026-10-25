import pytest
import requests
from datetime import datetime

from custom_components.novafos.pynovafos.novafos import HTTPFailed
from custom_components.novafos.pynovafos.novafos import Novafos


@pytest.fixture
def multiple_customers(mocker):
    customers = [
        {"Id": 12345678, "Number": 1234567.0, "StreetAddress": "First Street 1"},
        {"Id": 87654321, "Number": 7654321.0, "StreetAddress": "Second Street 2"},
    ]
    response = mocker.Mock(status_code=200)
    response.json.return_value = {"Customers": customers}
    mocker.patch("requests.get", return_value=response)
    return customers


def test_discover_multiple_customers(multiple_customers):
    api = Novafos(timezone="Europe/Copenhagen")
    assert api.get_customers("a" * 1200) == multiple_customers


def test_select_second_customer(multiple_customers):
    api = Novafos(timezone="Europe/Copenhagen", customer_id="87654321")
    api._get_customer_id()
    assert api._customer_id == "87654321"
    assert api._customer_number == "7654321.0"


def test_missing_selected_customer_does_not_fall_back(multiple_customers):
    api = Novafos(timezone="Europe/Copenhagen", customer_id="99999999")
    with pytest.raises(HTTPFailed):
        api._get_customer_id()
    assert api._customer_id == ""


def test_unconfigured_customer_preserves_legacy_selection(multiple_customers):
    api = Novafos(timezone="Europe/Copenhagen")
    api._get_customer_id()
    assert api._customer_id == "12345678"


@pytest.mark.parametrize("customer_id", [12345678, 87654321])
@pytest.mark.parametrize(("point_id", "meter_type"), [(101, "water"), (102, "heating")])
def test_address_and_meter_remain_selected_on_refresh(
    mocker, multiple_customers, customer_id, point_id, meter_type
):
    response = mocker.Mock(status_code=200)
    response.json.return_value = [
        {
            "IsActive": True,
            "ConsumptionTypeId": consumption_type,
            "MeasurementPointId": measurement_point,
            "InstallationId": customer_id,
            "Units": [{"Id": 1, "Name": "M3"}],
        }
        for consumption_type, measurement_point in [(6, 101), (5, 102)]
    ]
    post = mocker.patch("requests.post", return_value=response)
    api = Novafos(
        timezone="Europe/Copenhagen",
        customer_id=customer_id,
        measurement_point_id=point_id,
    )
    updated = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for _refresh in range(2):
        assert api.authenticate_using_access_token("a" * 1200, updated)
        assert post.call_args.kwargs["headers"]["Customer-Id"] == str(customer_id)
        customer = next(
            item for item in multiple_customers if item["Id"] == customer_id
        )
        assert post.call_args.kwargs["headers"]["Customer-Number"] == str(
            customer["Number"]
        )
        assert [meter["MeasurementPointId"] for meter in api.get_meter_types()] == [
            point_id
        ]
        assert set(api._meter_data) == {meter_type}
        multiple_customers.reverse()


def test_meter_discovery_uses_selected_customer(mocker, multiple_customers):
    response = mocker.Mock(status_code=200)
    response.json.return_value = [
        {
            "IsActive": True,
            "ConsumptionTypeId": 6,
            "MeasurementPointId": 101,
            "InstallationId": 1,
            "Units": [{"Id": 1}],
        },
        {
            "IsActive": True,
            "ConsumptionTypeId": 5,
            "MeasurementPointId": 102,
            "InstallationId": 2,
            "Units": [{"Id": 2}],
        },
    ]
    post = mocker.patch("requests.post", return_value=response)
    api = Novafos(timezone="Europe/Copenhagen")
    meters = api.get_meters("87654321")
    assert [meter["type"] for meter in meters] == ["water", "heating"]
    assert post.call_args.kwargs["headers"]["Customer-Id"] == "87654321"


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
    with pytest.raises(HTTPFailed) as error:
        novafos._get_customer_id()
    assert isinstance(error.value.__cause__, KeyError)
    assert error.value.__cause__.args == ("Id",)


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
    with pytest.raises(HTTPFailed) as error:
        novafos._get_customer_id()
    assert isinstance(error.value.__cause__, KeyError)
    assert error.value.__cause__.args == ("Number",)
