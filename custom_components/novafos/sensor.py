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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

import logging
_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, WATER_SENSOR_TYPES, HEATING_SENSOR_TYPES
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
    # The coordinator data is already populated and this means it is possible to 'auto-discover' which sensors to create:
    if "water" in coordinator.data:
        for description in WATER_SENSOR_TYPES:
            sensors.append(NovafosWaterSensor(name, coordinator, description))
    if "heating" in coordinator.data:
        for description in HEATING_SENSOR_TYPES:
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

        _LOGGER.debug(f"Registering Sensor for {description.name}")

        self._attr_name = f"{name} {description.name}"

        # To keep things backwards compatible - water does not get 'water' on the sensor value.
        if description.sensor_type != "water":
            self._attr_unique_id = f"{name.lower()}-{coordinator.supplierid}-{description.sensor_type}-{description.key}"
        else:
            self._attr_unique_id = f"{name.lower()}-{coordinator.supplierid}-{description.key}"

        # Note: Data is stored in self.coordinator.data[self.entity_description.key]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.entity_description.key in ("month", "day", "hour"):
            self._attrs["last_valid_date"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["LastValidDate"]
            self._attrs["average"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Average"]
            self._attrs["maximum"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Maximum"]
            self._attrs["minimum"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Minimum"]
            self._attrs["data"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Data"]
        elif self.entity_description.key == "hour":
            self._attrs["last_valid_date"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["LastValidDate"]
            self._attrs["average"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Average"]
            self._attrs["maximum"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Maximum"]
            self._attrs["minimum"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Minimum"]
        elif self.entity_description.key == "year":
            self._attrs["last_valid_date"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["LastValidDate"]
        else:
            self._attrs = {}
        return self._attrs

    @property
    def native_value(self) -> StateType:
        #_LOGGER.debug(f"QUERY NATIVE VALUE {self.entity_description.key}={cast(float, self.coordinator.data[self.entity_description.sensor_type]["hour"]["Data"][-1]["Value"])}")
        if self.entity_description.key == "hour":
            # Return the hour data from the dataset at the current hour
            # Condition: The hour data is exactly from yesterday.  Otherwise return None.
            # Probably not too useful, but all data is in the attributes.
            if datetime.strptime(self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["LastValidDate"], '%Y-%m-%dT%H:%M:%S').day == datetime.now().day-1:
                return cast(float, self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Data"][datetime.now().hour]["Value"])
            else:
                return None
        elif self.entity_description.key == "valid_date":
            return cast(datetime, datetime.strptime(self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Value"], '%Y-%m-%dT%H:%M:%S%z'))
        elif self.entity_description.key == "statistics":
            # State needs to be unknown as the data is in the past and not a current measurement.
            # If a state is set, this will go to the statistics too and make things look funny.
            return None
        elif self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Data"]:
            # If the data array is present, return its value.
            # In some instances the data-fetch cannot fetch data from the API endpoint
            return cast(float, self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["Data"][-1]["Value"])
        else:
            return None

