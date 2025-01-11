"""The novafos integration."""
from __future__ import annotations
from custom_components.novafos.coordinator import NovafosUpdateCoordinator
from custom_components.novafos.services import async_setup_services

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

PLATFORMS: list[Platform] = [Platform.SENSOR]

#async def async_setup(hass: HomeAssistant, config: dict) -> bool:
#    """Set up the Novafos component if we want to do more before the async_setup_entry()"""
#      hass.data[DOMAIN] = {}
#    or
#      hass.data.setdefault(DOMAIN, {})
#    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update.
       options are available at entry.options['']

       This code added because of reCAPTCHA login screen
    """
    _LOGGER.debug(f"Options updated: {entry.options}")
    await hass.data[DOMAIN][entry.entry_id]['coordinator'].async_request_refresh()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Novafos from a config entry."""
    _LOGGER.debug(f"Novafos ConfigData: {entry.data}")

    # Use the coordinator which handles regular fetch of API data.
    api = Novafos()
    coordinator = NovafosUpdateCoordinator(hass, api, entry)
    # If you do not want to retry setup on failure, use
    await coordinator.async_refresh()
    # This one repeats connecting to the API until first success.
    # NOTE: Disabled because of login screen reCAPTCHA - need a valid token to perform refresh.
    #await coordinator.async_config_entry_first_refresh()

    # Add the HomeAssistant specific API to the Novafos integration.
    # The Sensor entity in the integration will call function here to do its thing.
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator" : coordinator
    }

    # NOTE: Added because of login screen reCAPTCHA:
    # Option to add a listener which is called whenever configuration options is changed on the integration
    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass, coordinator)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_migrate_entry(hass, config_entry: ConfigEntry) -> bool:
    """Handle migration of setup entry data from one version to the next."""
    _LOGGER.info("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:

        new = {**config_entry.options}
        # Data:
        # {'supplierid': '...', 'password': '...', 'username': '...', 'access_token': <string>, 'access_token_date_updated': <string (and hidden)>}
        new['access_token'] = ""
        new['access_token_date_updated'] = ""

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, options=new)

        _LOGGER.info("Migration to version %s successful", config_entry.version)

    if config_entry.version == 2:

        new = {**config_entry.options}
        data = {**config_entry.data}
        # Data:
        # {'supplierid': '...', 'password': '...', 'username': '...', 'access_token': <string>, 'access_token_date_updated': <string (and hidden)>,
        #  'login_method: <selection>, 'novafos_login_docker': <string>}
        #
        # username and password is migrated to options because they are not necessary when using the token login method.
        data['login_method'] = "Token based"  # default to token login
        new['container_url'] = "http://localhost:5000/novafos-token/"
        new['username'] = data.pop('username')
        new['password'] = data.pop('password')
        config_entry.version = 3
        hass.config_entries.async_update_entry(config_entry, options=new)
        hass.config_entries.async_update_entry(config_entry, data=data)

        _LOGGER.info("Migration to version %s successful", config_entry.version)

    if config_entry.version == 3:
        new = {**config_entry.options}
        data = {**config_entry.data}

        _LOGGER.debug(new)
        _LOGGER.debug(data)

        if 'username' in new:
            del new['username']
        if 'password' in new:
            del new['password']
        if 'container_url' in new:
            del new['container_url']
        if 'supplierid' in data:
            del data['supplierid']
        del data['login_method']

        _LOGGER.debug("After:")
        _LOGGER.debug(new)
        _LOGGER.debug(data)

        hass.config_entries.async_update_entry(config_entry, data=data, options=new, version=4)

        _LOGGER.info("Migration to version %s successful", config_entry.version)


    return True
