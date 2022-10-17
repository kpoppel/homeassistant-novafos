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

        ######
        ## TODO: Preliminary placement - need to be an option
        ## NOTE: You can try this out and help out on github.  This is an early "expert" version
        ## Change localhost to the ip-address of your docker container host.
        ######
        #selenium_host_url = f"http://localhost:5000/novafos-token-test"
        selenium_host_url  = f"http://localhost:5000/novafos-token"

        try:
            # NOTE: Re-enable if login screen reCAPTCHA is removed:
            # if not await self.hass.async_add_executor_job(self.api.authenticate):
            # for now use this line:
            #if not await self.hass.async_add_executor_job(self.api.authenticate_using_access_token, self.entry.options['access_token'], self.entry.options['access_token_date_updated']):
            # for selenium based authentification use this line:
            if not await self.hass.async_add_executor_job(self.api.authenticate_using_selenium, selenium_host_url):
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