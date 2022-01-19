"""Sensor platform for Novafos integration."""
from __future__ import annotations
from typing import Any, cast
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import CONF_NAME
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import StateType
#from homeassistant.const import (VOLUME_CUBIC_METERS, DEVICE_CLASS_GAS)
#from homeassistant.components.sensor import (SensorEntity, STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL,
#                                            STATE_CLASS_TOTAL_INCREASING)
import logging
_LOGGER = logging.getLogger(__name__)

from custom_components.novafos.pynovafos.novafos import Novafos
from custom_components.novafos.pynovafos.models import TimeSeries

from . import HassNovafos
from .const import (DOMAIN, SENSOR_TYPES)
from .model import NovafosSensorDescription

async def async_setup_entry(hass:HomeAssistant, config:ConfigEntry, async_add_entities:AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    # Use the name for the unique id of each sensor. novafos_<supplierid>?
    name: str = config.data[CONF_NAME]
    coordinator: HassNovafos = hass.data[DOMAIN][config.entry_id]

    # The sensors are defined in the const.py file
    sensors: list[NovafosWaterSensor] = []
    for description in SENSOR_TYPES:
        sensors.append(NovafosWaterSensor(name, coordinator, description))

    async_add_entities(sensors)


class NovafosWaterSensor(SensorEntity):
    """Representation of a Sensor."""
    coordinator: HassNovafos
    entity_description: NovafosSensorDescription

    def __init__(self, name, coordinator, description):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entity_description = description
        self._attrs: dict[str, Any] = {}

        _LOGGER.debug(f"Registering Sensor for {self.entity_description.name}")

        self._attr_name = f"{name} {description.name}"
        self._attr_unique_id = f"{name.lower()}-{coordinator.supplierid}-{description.key}"
        self._sensor_data = coordinator.data

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self._sensor_data:
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
        if self._sensor_data:
            if self.entity_description.key == "hour":
                # Return the hour data from the dataset at the current hour
                # Probably not too useful, but all data is in the attributes.
                return cast(float, self._sensor_data["Data"][datetime.now().hour])["Value"]
            elif self.entity_description.key == "valid_date":
                return cast(datetime, datetime.strptime(self._sensor_data["Value"], '%Y-%m-%dT%H:%M:%S%z'))
            else:
                return cast(float, self._sensor_data["Data"][-1]["Value"])
        else:
            return None
        

    def update(self):
        """
        Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self.coordinator.update()
        # The HomeAssistent API frontend contains the data arranged by sensor name
        if self.coordinator.data:
            self._sensor_data = self.coordinator.data[self.entity_description.key]
            _LOGGER.debug(f"Updated status for {self._attr_name}")
        else:
            self._sensor_data = {}
            _LOGGER.debug(f"Updated status for {self._attr_name} resulted in empty dataset.")
