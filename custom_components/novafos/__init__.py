"""The novafos integration."""
from __future__ import annotations
from custom_components.novafos.coordinator import NovafosUpdateCoordinator

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# The Novafos integration - not on PyPi, just bundled here.
# Contrary to:
# https://developers.home-assistant.io/docs/creating_component_code_review#4-communication-with-devicesservices
from custom_components.novafos.pynovafos.novafos import Novafos

# Development help
import logging
_LOGGER = logging.getLogger(__name__)
import sys

PLATFORMS: list[Platform] = [Platform.SENSOR]

#async def async_setup(hass: HomeAssistant, config: dict) -> bool:
#    """Set up the Novafos component if we want to do more before the async_setup_entry()"""
#      hass.data[DOMAIN] = {}
#    or
#      hass.data.setdefault(DOMAIN, {})
#    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Novafos from a config entry."""
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    
    _LOGGER.debug(f"Novafos ConfigData: {entry.data}")

    # Use the coordinator which handles regular fetch of API data.
    api = Novafos(username, password, supplierid)
    coordinator = NovafosUpdateCoordinator(hass, api, entry)
    # If you do not want to retry setup on failure, use
    #await coordinator.async_refresh()
    # This one repeats connecting to the API until first success.
    await coordinator.async_config_entry_first_refresh()

    # Add the HomeAssistant specific API to the Novafos integration.
    # The Sensor entity in the integration will call function here to do its thing.
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator" : coordinator
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
