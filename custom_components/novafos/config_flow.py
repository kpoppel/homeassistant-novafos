"""Config flow for Novafos integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

# Username and passwor dis the ones for the website.
# Supplier ID is the "customer database identifier", a 6 digit number gotten off the website.
DATA_SCHEMA = vol.Schema({"username": str, "password": str, "supplierid": str})


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    
    hub = PlaceholderHub(data["host"])

    if not await hub.authenticate(data["username"], data["password"], data["supplierid"]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    # Maybe
    supplierid = data["supplierid"]
    return {"title": f"Novafos {supplierid}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eforsyning."""

    VERSION = 1
    
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                #info = await validate_input(self.hass, user_input)
                supplierid = user_input["supplierid"]
                info = f"Novafos {supplierid}"
                return self.async_create_entry(title=info, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
