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


def meter_statistics_key(data, meter_type):
    """Scope new entries to a customer and meter, preserving legacy IDs."""
    if "customer_id" in data and "measurement_point_id" in data:
        return f"{data['customer_id']}_{data['measurement_point_id']}_{meter_type}"
    return meter_type


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
        state_class=SensorStateClass.TOTAL,
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
        state_class=SensorStateClass.TOTAL,
    ),
)
