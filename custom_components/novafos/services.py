from homeassistant.core import HomeAssistant, callback, ServiceCall
import voluptuous as vol
from datetime import datetime

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator
)

# Development help
import logging
_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN

DEFAULT_NAME = "none"

async def async_setup_services(hass: HomeAssistant, coordinator: DataUpdateCoordinator):
	DATA_SCHEMA = vol.Schema(
		{
			vol.Required("access_token", default=""): str,
			vol.Required("access_token_date_updated", default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S")): str
		}
	)
	@callback
	async def async_update_token(call: ServiceCall):
		"""Handle the service action call."""
		# Update the coordinator data fields.
		_LOGGER.debug(f"Update via action service call initiated.")
		# The user has to configure for token based flow.
		# Okay, it could be possible to do this withot this requirement, but since all other login methis are not working, this requirement will work.
		if coordinator.entry.data['login_method'] != "Token based":
			_LOGGER.error(f"Service action called, but token based flow is not configured.")
			return False
		coordinator.access_token = call.data['access_token']
		coordinator.access_token_date_updated = call.data['access_token_date_updated']
		# Then call the coordinator to update itself.
		await coordinator.async_refresh()

	# Add service to receive a login token
	hass.services.async_register(
		DOMAIN,
		"update_token",
		async_update_token,
		schema=DATA_SCHEMA)
	
	# Indicate setup completed okay.
	_LOGGER.debug("Novafos action service setup completed")
	return True
