from homeassistant.core import HomeAssistant, callback, ServiceCall
import voluptuous as vol
from datetime import datetime

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import DOMAIN

# Development help
import logging

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "none"


async def async_setup_services(hass: HomeAssistant, coordinator: DataUpdateCoordinator):
    DATA_SCHEMA = vol.Schema(
        {
            vol.Required("access_token", default=""): str,
            vol.Required("access_token_date_updated", default=""): str,
        }
    )

    @callback
    async def async_update_token(call: ServiceCall):
        """Handle the service action call."""
        # Update the coordinator data fields.
        _LOGGER.debug("Update via action service call initiated.")

        coordinator.access_token = call.data["access_token"]
        if call.data["access_token_date_updated"] == "":
            coordinator.access_token_date_updated = datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
        else:
            coordinator.access_token_date_updated = call.data[
                "access_token_date_updated"
            ]
        # Then call the coordinator to update itself.
        # await coordinator.async_refresh()

    # Add service to receive a login token
    hass.services.async_register(
        DOMAIN, "update_token", async_update_token, schema=DATA_SCHEMA
    )

    # Indicate setup completed okay.
    _LOGGER.debug("Novafos action service setup completed")
    return True
