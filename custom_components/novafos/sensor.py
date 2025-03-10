"""Sensor platform for Novafos integration."""

from __future__ import annotations
from typing import Any

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

from .const import (
    DOMAIN,
    WATER_SENSOR_TYPES,
    HEATING_SENSOR_TYPES,
    EXTRA_WATER_SENSOR_TYPES,
    EXTRA_HEATING_SENSOR_TYPES,
)

from .model import NovafosSensorDescription

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    # Use the name for the unique id of each sensor. novafos_<supplierid>?
    name: str = config.data[CONF_NAME]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id][
        "coordinator"
    ]
    # coordinator has a 'data' field.  This is set to the returned API data value.
    # _async_update_data updates the field.
    # From this field the sensors will get their values afterwards.

    # The sensors are defined in the const.py file
    sensors: list[NovafosWaterSensor] = []
    # The coordinator data is already populated and this means it is possible to 'auto-discover' which sensors to create:
    if "water" in coordinator.data[0]:
        for description in WATER_SENSOR_TYPES:
            sensors.append(NovafosWaterSensor(name, coordinator, description))
            # _LOGGER.debug("Adding Novafos sensor %s", description.name)
        if config.data["use_grouped_sensors"]:
            for description in EXTRA_WATER_SENSOR_TYPES:
                sensors.append(NovafosWaterSensor(name, coordinator, description))
                # _LOGGER.debug("Adding Novafos sensor %s", description.name)

    if "heating" in coordinator.data[0]:
        for description in HEATING_SENSOR_TYPES:
            sensors.append(NovafosWaterSensor(name, coordinator, description))
        if config.data["use_grouped_sensors"]:
            for description in EXTRA_HEATING_SENSOR_TYPES:
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
        self._attr_unique_id = (
            f"{name.lower()}-{description.sensor_type}-{description.key}"
        )

        # Note: Data is stored in self.coordinator.data

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes.
        Attributes could include the last total yearly consumption.
        This value may be used in a template sensor which can in turn be
        used in the energy dashboard.
        TODO: If yearly values should be included it is probably a good idea
              to just make that one extra REST API call and the the latest
              year total.  Alternately the sum of all hours since start-of-year
              is to be calculated on every fetch. That is many data points
              at the end of the year.
        """
        _LOGGER.debug(self.coordinator.data)
        if (
            self.entity_description.key == "statistics"
            and self.coordinator.data[1] is not None
        ):
            self._attrs["year_total"] = self.coordinator.data[1][
                self.entity_description.sensor_type
            ]["Data"][-1]["Value"]
        #     self._attrs["last_valid_date"] = self.coordinator.data[self.entity_description.sensor_type][self.entity_description.key]["LastValidDate"]
        else:
            self._attrs = {}
        return self._attrs

        # self._attrs = {}

    @property
    def native_value(self) -> StateType:
        # State needs to be unknown as the data is in the past and not a current measurement.
        # If a state is set, this will go to the statistics too and make things look funny.
        # return self.coordinator.data[2]
        return None
