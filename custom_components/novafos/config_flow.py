"""Config flow for Novafos integration."""
from __future__ import annotations

from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import selector

from .const import DEFAULT_NAME, DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

from datetime import datetime

from custom_components.novafos.pynovafos.novafos import Novafos, LoginFailed, HTTPFailed


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Returns True or False.  The API is not built for async operation
    # therefore it is wrapped in an async executor function.
    # NOTE: disabled due to reCAPTCHA login screen
    #try:
    #    api = Novafos(data["username"], data["password"], data["supplierid"])
    #    await hass.async_add_executor_job(api.authenticate)
    #except LoginFailed:
    #    raise InvalidAuth
    #except HTTPFailed:
    #    raise CannotConnect
    # NOTE: ^^^^ to here

    # Return info to store in the config entry.
    # title becomes the title on the integrations screen in the UI
    return {"title": f"Novafos {data['supplierid']}"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for novafos."""

    VERSION = 3

    data: Optional[Dict[str, Any]]
    options: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        # Username and password is the ones for the website.
        # Supplier ID is the "customer database identifier", a 6 digit number gotten off the website.
        data_schema = {
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required("supplierid"): str
        }
        data_schema["login_method"] = selector({
            "select": {
                "options": ["Token based", "Automated browser login", "Username/password"],
                "mode": "dropdown"
            }
        })

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(data_schema)
            )

        errors: Dict[str, str] ={}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        if not errors:
            # Input is okay, ready for step two
            self.data = user_input
            self.options = {}
            return await self.async_step_step_2()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_step_2(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle options during setup. These functions are called at least twice.
           First round hasuser_Data = None, and shows the form.  Then it is called again with user_data set.
        """
        if user_input is not None:
            # Validate - not implemented
            _LOGGER.debug(user_input)
            _LOGGER.debug(self.data)
            _LOGGER.debug(self.options)
            # Anyway, set options related to the chosen login method
            if self.data.get("login_method") == "Token based":
                self.options["access_token"] = user_input.get("access_token")
                self.options["access_token_date_updated"] = user_input.get("access_token_date_updated")
            elif self.data.get("login_method") == "Username/password":
                self.options["username"] = user_input.get("username")
                self.options["password"] = user_input.get("password")
            else: #"Automated browser login"
                self.options["username"] = user_input.get("username")
                self.options["password"] = user_input.get("password")
                self.options["container_url"] = user_input.get("container_url")
            
            return self.async_create_entry(title=f"{self.data['name']} {self.data['supplierid']}", data=self.data, options=self.options)

        # Default to empty string.  This is used to make sure we can detect reasonable changes
        # to avoid hitting the API with bad data.
        data_schema = None
        if self.data.get("login_method") == "Token based":
            data_schema = {
                    vol.Required(
                        "access_token",
                        default=""
                    ): str,
                    vol.Required(
                        "access_token_date_updated",
                        default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    ): str,
                }
        elif self.data.get("login_method") == "Username/password":
            data_schema = {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
        else: #"Automated browser login"
            data_schema = {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required(
                        "container_url",
                        default="http://localhost:5000/novafos-token/"
                    ): str,
                }

        return self.async_show_form(
                step_id="step_2",  #<- this matches the function name..
                data_schema=vol.Schema(data_schema)
            )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an option flow.  This is the flow when reconfiguring after adding the integration"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Default to empty string.  This is used to make sure we can detect reasonable changes
        # to avoid hitting the API with bad data.
        data_schema = None
        if self.config_entry.data.get("login_method") == "Token based":
            data_schema = {
                    vol.Required(
                        "access_token",
                        default=""
                    ): str,
                    vol.Required(
                        "access_token_date_updated",
                        default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    ): str,
                }
        elif self.config_entry.data.get("login_method") == "Username/password":
            data_schema = {
                    vol.Required(
                        "username",
                        default=self.config_entry.options['username']
                    ): str,
                    vol.Required(
                        "password",
                        default=self.config_entry.options['password']
                    ): str,
                }
        else: #"Automated browser login"
            data_schema = {
                    vol.Required(
                        "username",
                        default=self.config_entry.options['username']
                    ): str,
                    vol.Required(
                        "password",
                        default=self.config_entry.options['password']
                    ): str,
                    vol.Required(
                        "username",
                        default=self.config_entry.options['username']
                    ): str,
                    vol.Required(
                        "container_url",
                        default=self.config_entry.options['container_url']
                    ): str,
                }


        return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(data_schema)
            )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""