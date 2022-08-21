"""DataUpdateCoordinator for Novafos."""
from __future__ import annotations

from custom_components.novafos.pynovafos.novafos import Novafos
from .sensor import NovafosWaterSensor

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import HomeAssistantError

from .const import MIN_TIME_BETWEEN_UPDATES

import logging
_LOGGER = logging.getLogger(__name__)

class NovafosUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator for Novafos."""
    def __init__(
        self,
        hass: HomeAssistant,
        api: Novafos,
        entry: ConfigEntry,
    ) -> None:
        """Initialize DataUpdateCoordinator"""
        self.api = api
        self.hass = hass
        self.supplierid = entry.data['supplierid']
        
        super().__init__(
            hass,
            _LOGGER,
            name="Novafos",
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )

    async def _async_update_data(self):
        """Get the data for Novafos."""
        try:
            if not await self.hass.async_add_executor_job(self.api.authenticate):
                raise InvalidAuth
        except InvalidAuth as error:
            raise ConfigEntryAuthFailed from error

        # Retrieve latest data from the API
        try:
            data = await self.hass.async_add_executor_job(self.api.get_latest)
        except Exception as error:
            raise ConfigEntryNotReady from error

        # Return the data
        # The data is stored in the coordinator as a .data field.
        return data

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""