"""Constants for the Novafos integration."""

from __future__ import annotations
from typing import Final

# Get Sensor classification and unit definitions:
from homeassistant.components.sensor import SensorStateClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.const import UnitOfVolume

from .model import NovafosSensorDescription

DOMAIN = "novafos"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "Novafos"

# NOTE:
#  All consumption data can be derived from the statistics sensor.
#  The sensor will always have state "unknown" because data is only relevant in the past.
#  Instead use the statistics charts and cards to get data out.
WATER_SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        sensor_type="water",
        key="statistics",
        name="Water statistics",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

EXTRA_WATER_SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        sensor_type="water",
        key="statistics_day",
        name="Water statistics day",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NovafosSensorDescription(
        sensor_type="water",
        key="statistics_week",
        name="Water statistics week",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NovafosSensorDescription(
        sensor_type="water",
        key="statistics_month",
        name="Water statistics month",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NovafosSensorDescription(
        sensor_type="water",
        key="statistic_years",
        name="Water statistics year",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

HEATING_SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        sensor_type="heating",
        key="statistics",
        name="Heating statistics",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

EXTRA_HEATING_SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        sensor_type="heating",
        key="statistics_day",
        name="Heating statistics day",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NovafosSensorDescription(
        sensor_type="heating",
        key="statistics_week",
        name="Heating statistics week",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NovafosSensorDescription(
        sensor_type="heating",
        key="statistics_month",
        name="Heating statistics month",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NovafosSensorDescription(
        sensor_type="heating",
        key="statistic_years",
        name="Heating statistics year",
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
