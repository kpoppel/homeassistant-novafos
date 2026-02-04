"""Config flow for Novafos integration."""

from __future__ import annotations

from typing import Any
from datetime import datetime

import voluptuous as vol

from homeassistant import (
    config_entries,
)
from .const import DOMAIN

from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME

from .const import DEFAULT_NAME

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
    ) -> FlowResult:
        """Handle the initial step."""
        # Setup a name for the integration instance
        data_schema = {
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional("use_grouped_sensors", default=False): bool,
        }

        # First run - present dialog:
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(data_schema)
            )

        # Assign a unique ID to the flow and abort the flow
        # if another flow with the same unique ID is in progress
        await self.async_set_unique_id(f"{user_input[CONF_NAME]}")

        # Abort the flow if a config entry with the same unique ID exists
        self._abort_if_unique_id_configured()

        # Regardless of using manual token flow or service action we require a valid token to seed the sensor setup.
        # Could have done this in a nother way though:  checkbox to select water, heating or both and a static setup.
        self.data = user_input
        self.options = {}
        return await self.async_step_manual_token_flow()

    async def async_step_manual_token_flow(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options during setup. These functions are called at least twice.
        First round has user_input = None, and shows the form.  Then it is called again with user_input set.
        """

        # First time called:
        if user_input is None:
            # Default to empty string.  This is used to make sure we can detect reasonable changes
            # to avoid hitting the API with bad data.
            data_schema = {
                vol.Required("access_token", default=""): str,
            }
            return self.async_show_form(
                step_id="manual_token_flow",  # <- this matches the function name..
                data_schema=vol.Schema(data_schema),
            )

        # Validate - not implemented
        _LOGGER.debug(user_input)
        _LOGGER.debug(self.data)
        _LOGGER.debug(self.options)
        # Anyway, set options related to the chosen login method
        self.options["access_token"] = user_input.get("access_token")
        # Hidden field:
        self.options["access_token_date_updated"] = datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        return self.async_create_entry(
            title=f"Novafos: {self.data['name']}", data=self.data, options=self.options
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
    ) -> FlowResult:
        """Handle options flow."""

        # First time called:
        if user_input is None:
            # Default to empty string.  This is used to make sure we can detect reasonable changes
            # to avoid hitting the API with bad data.
            data_schema = None
            data_schema = {
                vol.Required("access_token", default=""): str,
            }

            return self.async_show_form(
                step_id="init", data_schema=vol.Schema(data_schema)
            )

        user_input["access_token_date_updated"] = datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        return self.async_create_entry(title="", data=user_input)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
