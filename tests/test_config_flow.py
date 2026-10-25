"""Address and measurement-point selection tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.novafos.config_flow import ConfigFlow
from custom_components.novafos.pynovafos.novafos import HTTPFailed, LoginFailed
from homeassistant.data_entry_flow import AbortFlow


@pytest.fixture
def flow(mocker):
    api = mocker.patch("custom_components.novafos.config_flow.Novafos").return_value
    api.get_customers.return_value = [
        {"Id": 11, "Number": 101, "StreetAddress": "First Street 1"},
        {"Id": 22, "Number": 202, "StreetAddress": "Second Street 2"},
    ]
    api.get_meters.return_value = [
        {"type": "water", "MeasurementPointId": 1001},
        {"type": "heating", "MeasurementPointId": 1002},
    ]

    async def execute(function, *args):
        return function(*args)

    instance = ConfigFlow()
    instance.hass = SimpleNamespace(
        config=SimpleNamespace(time_zone="Europe/Copenhagen"),
        async_add_executor_job=execute,
    )
    instance.async_show_form = Mock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    instance.async_create_entry = Mock(
        side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
    )
    instance.async_set_unique_id = AsyncMock()
    instance._abort_if_unique_id_configured = Mock()
    instance.data = {"name": "Novafos"}
    instance.options = {}
    return instance, api


@pytest.mark.asyncio
async def test_address_then_metering(flow):
    instance, api = flow
    result = await instance.async_step_manual_token_flow({"access_token": "token"})
    assert result["step_id"] == "address"
    result = await instance.async_step_address({"customer_id": "22"})
    api.get_meters.assert_called_once_with("22")
    assert result["step_id"] == "metering"
    result = await instance.async_step_metering({"measurement_point_id": "1002"})
    assert result["type"] == "create_entry"
    assert result["data"]["customer_id"] == "22"
    assert result["data"]["measurement_point_id"] == "1002"
    assert result["data"]["meter_type"] == "heating"
    assert result["options"]["access_token"] == "token"
    instance.async_set_unique_id.assert_awaited_once_with("22_1002")
    instance._abort_if_unique_id_configured.assert_called_once()


@pytest.mark.asyncio
async def test_single_address_is_automatically_selected(flow):
    instance, api = flow
    api.get_customers.return_value = api.get_customers.return_value[:1]
    result = await instance.async_step_manual_token_flow({"access_token": "token"})
    assert result["step_id"] == "metering"
    assert instance.data["customer_id"] == "11"
    api.get_meters.assert_called_once_with("11")


@pytest.mark.asyncio
async def test_single_address_and_meter_are_automatically_selected(flow):
    instance, api = flow
    api.get_customers.return_value = api.get_customers.return_value[:1]
    api.get_meters.return_value = api.get_meters.return_value[:1]
    result = await instance.async_step_manual_token_flow({"access_token": "token"})
    assert result["type"] == "create_entry"
    assert result["data"]["measurement_point_id"] == "1001"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "message"),
    [(LoginFailed(), "invalid_auth"), (HTTPFailed(), "cannot_connect")],
)
async def test_token_errors_allow_retry(flow, error, message):
    instance, api = flow
    api.get_customers.side_effect = error
    result = await instance.async_step_manual_token_flow({"access_token": "token"})
    assert result["step_id"] == "manual_token_flow"
    assert result["errors"] == {"base": message}


@pytest.mark.asyncio
async def test_no_addresses(flow):
    instance, api = flow
    api.get_customers.return_value = []
    result = await instance.async_step_manual_token_flow({"access_token": "token"})
    assert result["errors"] == {"base": "no_addresses"}


@pytest.mark.asyncio
async def test_no_meters_allows_another_address(flow):
    instance, api = flow
    await instance.async_step_manual_token_flow({"access_token": "token"})
    api.get_meters.return_value = []
    result = await instance.async_step_address({"customer_id": "22"})
    assert result["step_id"] == "address"
    assert result["errors"] == {"base": "no_meters"}


@pytest.mark.asyncio
async def test_duplicate_meter_aborts_instead_of_creating_entry(flow):
    instance, api = flow
    await instance.async_step_manual_token_flow({"access_token": "token"})
    await instance.async_step_address({"customer_id": "22"})
    instance._abort_if_unique_id_configured.side_effect = AbortFlow(
        "already_configured"
    )
    with pytest.raises(AbortFlow):
        await instance.async_step_metering({"measurement_point_id": "1002"})
    instance.async_create_entry.assert_not_called()


@pytest.mark.asyncio
async def test_four_entries_with_same_name_have_distinct_identities(flow):
    instance, api = flow
    identities = set()
    for customer_id in ("11", "22"):
        for point_id in ("1001", "1002"):
            await instance.async_step_user({"name": "Novafos"})
            await instance.async_step_manual_token_flow({"access_token": "token"})
            await instance.async_step_address({"customer_id": customer_id})
            await instance.async_step_metering({"measurement_point_id": point_id})
            identities.add(instance.async_set_unique_id.call_args.args[0])
    assert len(identities) == 4


@pytest.mark.asyncio
async def test_token_expiring_during_meter_discovery_allows_retry(flow):
    instance, api = flow
    await instance.async_step_manual_token_flow({"access_token": "token"})
    api.get_meters.side_effect = LoginFailed()
    result = await instance.async_step_address({"customer_id": "22"})
    assert result["step_id"] == "manual_token_flow"
    assert result["errors"] == {"base": "invalid_auth"}
