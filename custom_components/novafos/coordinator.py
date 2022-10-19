"""DataUpdateCoordinator for Novafos."""
from __future__ import annotations

from custom_components.novafos.pynovafos.novafos import Novafos
from .sensor import NovafosWaterSensor

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import HomeAssistantError

from datetime import datetime as dt
from datetime import timedelta
from random import randrange

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
        self.entry = entry
        self.supplierid = entry.data['supplierid']
        # Set last time we updated to right now.
        self.last_update = dt.now()
        
        super().__init__(
            hass,
            _LOGGER,
            name="Novafos",
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )

    async def _async_update_data(self):
        """Get the data for Novafos.
           Manipulate self.update_interval so that updates are happening randomly from 02:00 to 07:00 once per day.
        """
        now = dt.now()
        self.update_interval = (now.replace(hour=2, minute=0, second=0) - now) + timedelta(hours=24, minutes=randrange(5*60))
        # Test shorter update interfal - no this ONLY with the test endpoint!!!
        #  Also make sure to not poll data from KMD as you may get flagged for abuse.
        #    self.update_interval = timedelta(seconds=randrange(20))
        _LOGGER.debug(f"Next update at: {now +  self.update_interval}")

        try:
            # Let us use one of the three types of login - as far as we know, only token based and experimental selenium
            # login works.
            if self.entry.data['login_method'] == "Token based":
               if not await self.hass.async_add_executor_job(self.api.authenticate_using_access_token, self.entry.options['access_token'], self.entry.options['access_token_date_updated']):
                    raise InvalidAuth
            elif  self.entry.data['login_method'] == "Username/password":
                if not await self.hass.async_add_executor_job(self.api.authenticate):
                    raise InvalidAuth
            else:
                if not await self.hass.async_add_executor_job(self.api.authenticate_using_selenium, self.entry.options['container_url']):
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