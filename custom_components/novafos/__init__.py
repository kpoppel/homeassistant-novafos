"""The novafos integration."""
from __future__ import annotations
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES

# The Novafos integration - not on PyPi, just bundled here.
# Contrary to:
# https://developers.home-assistant.io/docs/creating_component_code_review#4-communication-with-devicesservices
from custom_components.novafos.pynovafos.novafos import Novafos

# Development help
import logging
import sys
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

#async def async_setup(hass: HomeAssistant, config: dict) -> bool:
#    """Set up the Novafos component if we want to do more before the async_setup_entry()"""
#      hass.data[DOMAIN] = {}
#    or
#      hass.data.setdefault(DOMAIN, {})
#    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up novafos from a config entry."""
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    
    _LOGGER.debug("Novafos ConfigData: {entry.data}")

    # Add the HomeAssistant specific API to the Novafos integration.
    # The Sensor entity in the integration will call function here to do its thing.
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = HassNovafos(username, password, supplierid)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

from homeassistant.util import Throttle
import requests

class HassNovafos:
    """Home-Assistant specific API for Novafos."""
    def __init__(self, username, password, supplierid):
        self.supplierid = supplierid
        self.data = {}
        self._client = Novafos(username, password, supplierid)
        self._last_session = None
        _LOGGER.debug("A HassNovafos class was created")

    # The Throttle annotation sets a limit to how often we update data. See const.py
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug("Fetching data from Novafos")
        # If debugging, the try/catch can be annoying. Use this line and comment away the rest.
        if self._last_session == None or (datetime.now()-self._last_session) >= timedelta(minutes=60):
            self.data = self._client.get_latest()
            self._last_session = datetime.now()

#        try: 
#            data = self._client.get_latest()
#            if data.status == 200:
#                self.data = data
#            else:
#                _LOGGER.warn(f"Error from novafos: {data.status} - {data.detailed_status}")
#        except requests.exceptions.HTTPError as he:
#            message = None
#            if he.response.status_code == 401:
#                message = f"Unauthorized error while accessing novafos. Wrong or expired credentials or supplier ID?"
#            else:
#                message = f"Exception: {e}"
#
#            _LOGGER.warn(message)
#        except: 
#            e = sys.exc_info()[0]
#            _LOGGER.warn(f"Exception: {e}")
        _LOGGER.debug("Done fetching data from Novafos")
