"""Sensor platform for Novafos integration."""
from __future__ import annotations
from typing import Any, cast
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import CONF_NAME
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

import logging
_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, SENSOR_TYPES
from .model import NovafosSensorDescription

async def async_setup_entry(
    hass:HomeAssistant,
    config:ConfigEntry,
    async_add_entities:AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    # Use the name for the unique id of each sensor. novafos_<supplierid>?
    name: str = config.data[CONF_NAME]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]["coordinator"]
    # coordinator has a 'data' field.  This is set to the returned API data value.
    # _async_update_data updates the field.
    # From this field the sensors will get their values afterwards.

    # The sensors are defined in the const.py file
    sensors: list[NovafosWaterSensor] = []
    for description in SENSOR_TYPES:
        sensors.append(NovafosWaterSensor(name, coordinator, description))

    async_add_entities(sensors)


class NovafosWaterSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""
    entity_description: NovafosSensorDescription

    def __init__(self, name, coordinator, description):
        """Initialise the coordinator"""
        super().__init__(coordinator)

        """Initialize the sensor."""
        self.entity_description = description
        self._attrs: dict[str, Any] = {}

        _LOGGER.debug(f"Registering Sensor for {self.entity_description.name}")

        self._attr_name = f"{name} {description.name}"
        self._attr_unique_id = f"{name.lower()}-{coordinator.supplierid}-{description.key}"
        # Data is resolved from here - relies on the fact that first sync is successful:
        self._sensor_data = coordinator.data[self.entity_description.key]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.entity_description.key in ("month", "day", "hour"):
            self._attrs["last_valid_date"] = self._sensor_data["LastValidDate"]
            self._attrs["average"] = self._sensor_data["Average"]
            self._attrs["maximum"] = self._sensor_data["Maximum"]
            self._attrs["minimum"] = self._sensor_data["Minimum"]
            self._attrs["data"] = self._sensor_data["Data"]
        elif self.entity_description.key == "year":
            self._attrs["last_valid_date"] = self._sensor_data["LastValidDate"]
        else:
            self._attrs = {}
        return self._attrs

    @property
    def native_value(self) -> StateType:
        if self.entity_description.key == "hour":
            # Return the hour data from the dataset at the current hour
            # Condition: The hour data is exactly from yesterday.  Otherwise return None.
            # Probably not too useful, but all data is in the attributes.
            if datetime.strptime(self._sensor_data["LastValidDate"], '%Y-%m-%dT%H:%M:%S').day == datetime.now().day-1:
                return cast(float, self._sensor_data["Data"][datetime.now().hour])["Value"]
            else:
                return None
        elif self.entity_description.key == "valid_date":
            return cast(datetime, datetime.strptime(self._sensor_data["Value"], '%Y-%m-%dT%H:%M:%S%z'))
        else:
            return cast(float, self._sensor_data["Data"][-1]["Value"])
