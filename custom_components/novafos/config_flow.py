"""Config flow for Novafos integration."""

from __future__ import annotations

from typing import Any
from datetime import datetime

import voluptuous as vol

from .const import DOMAIN

from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME

from .const import DEFAULT_NAME
from .pynovafos.novafos import HTTPFailed, LoginFailed, Novafos

import logging

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Returns True or False.  The API is not built for async operation
    # therefore it is wrapped in an async executor function.
    # NOTE: disabled due to reCAPTCHA login screen
    # try:
    #    api = Novafos(data["username"], data["password"], data["supplierid"])
    #    await hass.async_add_executor_job(api.authenticate)
    # except LoginFailed:
    #    raise InvalidAuth
    # except HTTPFailed:
    #    raise CannotConnect
    # NOTE: ^^^^ to here

    # Return info to store in the config entry.
    # title becomes the title on the integrations screen in the UI
    return {"title": f"Novafos: {data['name']}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for novafos."""

    VERSION = 4
    MINOR_VERSION = 0

    data: dict[str, Any] | None
    options: dict[str, Any] | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Setup a name for the integration instance
        data_schema = {
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional("use_external_statistics", default=True): bool,
        }

        # First run - present dialog:
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(data_schema)
            )

        # Regardless of using manual token flow or service action we require a valid token to seed the sensor setup.
        # Could have done this in a nother way though:  checkbox to select water, heating or both and a static setup.
        self.data = user_input
        self.options = {}
        return await self.async_step_manual_token_flow()

    async def async_step_manual_token_flow(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate a token and discover the available addresses."""
        errors = {}
        if user_input is not None:
            self._api = Novafos(timezone=self.hass.config.time_zone)
            try:
                customers = await self.hass.async_add_executor_job(
                    self._api.get_customers, user_input["access_token"]
                )
                self._customers = {
                    str(customer["Id"]): customer for customer in customers
                }
            except LoginFailed:
                errors["base"] = "invalid_auth"
            except (HTTPFailed, KeyError, TypeError):
                errors["base"] = "cannot_connect"
            else:
                if self._customers:
                    self.options["access_token"] = user_input["access_token"]
                    self.options["access_token_date_updated"] = datetime.now().strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                    return await self.async_step_address()
                errors["base"] = "no_addresses"
        return self.async_show_form(
            step_id="manual_token_flow",
            data_schema=vol.Schema({vol.Required("access_token"): str}),
            errors=errors,
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select an address, automatically selecting the only address."""
        errors = {}
        if user_input is None and len(self._customers) == 1:
            user_input = {"customer_id": next(iter(self._customers))}
        if user_input is not None:
            customer_id = user_input["customer_id"]
            if customer_id not in self._customers:
                errors["base"] = "invalid_address"
            else:
                try:
                    meters = await self.hass.async_add_executor_job(
                        self._api.get_meters, customer_id
                    )
                except LoginFailed:
                    return self.async_show_form(
                        step_id="manual_token_flow",
                        data_schema=vol.Schema({vol.Required("access_token"): str}),
                        errors={"base": "invalid_auth"},
                    )
                except HTTPFailed:
                    errors["base"] = "cannot_connect"
                else:
                    self._meters = {
                        str(meter["MeasurementPointId"]): meter for meter in meters
                    }
                    if self._meters:
                        customer = self._customers[customer_id]
                        self.data["customer_id"] = customer_id
                        self.data["address"] = (
                            customer.get("StreetAddress") or customer_id
                        )
                        return await self.async_step_metering()
                    errors["base"] = "no_meters"
        addresses = {
            customer_id: ", ".join(
                str(part)
                for part in (
                    customer.get("StreetAddress"),
                    customer.get("City"),
                    customer.get("Number"),
                )
                if part is not None and part != ""
            )
            or customer_id
            for customer_id, customer in self._customers.items()
        }
        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema({vol.Required("customer_id"): vol.In(addresses)}),
            errors=errors,
        )

    async def async_step_metering(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select one water or heating measurement point."""
        errors = {}
        if user_input is None and len(self._meters) == 1:
            user_input = {"measurement_point_id": next(iter(self._meters))}
        if user_input is not None:
            measurement_point_id = user_input["measurement_point_id"]
            if measurement_point_id not in self._meters:
                errors["base"] = "invalid_meter"
            else:
                meter = self._meters[measurement_point_id]
                await self.async_set_unique_id(
                    f"{self.data['customer_id']}_{measurement_point_id}"
                )
                self._abort_if_unique_id_configured()
                self.data["measurement_point_id"] = measurement_point_id
                self.data["meter_type"] = meter["type"]
                return self.async_create_entry(
                    title=f"{self.data['name']}: {self.data['address']} ({meter['type']})",
                    data=self.data,
                    options=self.options,
                )
        meters = {
            point_id: f"{meter['type'].title()} ({point_id})"
            for point_id, meter in self._meters.items()
        }
        return self.async_show_form(
            step_id="metering",
            data_schema=vol.Schema(
                {vol.Required("measurement_point_id"): vol.In(meters)}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    # def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
    #    pass


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an option flow.  This is the flow when reconfiguring after adding the integration"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""

        # First time called:
        if user_input is None:
            # Default to empty string.  This is used to make sure we can detect reasonable changes
            # to avoid hitting the API with bad data.
            data_schema = {
                vol.Optional("access_token", default=""): str,
                vol.Optional(
                    "use_external_statistics",
                    default=self._config_entry.options.get(
                        "use_external_statistics",
                        self._config_entry.data.get("use_external_statistics", True),
                    ),
                ): bool,
            }

            return self.async_show_form(
                step_id="init", data_schema=vol.Schema(data_schema)
            )

        if user_input.get("access_token"):
            user_input["access_token_date_updated"] = datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
        else:
            user_input["access_token"] = self._config_entry.options.get(
                "access_token", ""
            )
            user_input["access_token_date_updated"] = self._config_entry.options.get(
                "access_token_date_updated", ""
            )
        return self.async_create_entry(title="", data=user_input)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
