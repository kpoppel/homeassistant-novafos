"""Constants for the Novafos integration."""
from __future__ import annotations
from typing import Final
from datetime import timedelta
from homeassistant.const import (VOLUME_CUBIC_METERS, DEVICE_CLASS_GAS, DEVICE_CLASS_DATE)
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT

from .model import NovafosSensorDescription

DOMAIN = "novafos"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "Novafos"

# Every 6 hours seems appropriate to get an update ready in the morning
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Sure, let's bash the API service.. But useful when trying to get results fast.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

# Sensors:
# NOTE: For ALL sensors it is NOT the current day number which is received.
#       If using the history graph the data shown will be from the past.
#       The attributes of the sensor will tell the correct date of the sensor.
#       Use this information with a template sensor or apexcharts data generator to get it right.
# *  Year Total (resets once per year)
#    The year total sensor will have attributes storing all data points (for apexcharts)
# *  Month Total (resets once per month) - attribute stating last valid data date
# *  Day Total for "last valid" -  attribute stating last valid data date
# *  Make an hourly "last valid" sensor which returns the data from the correct hour some days ago.
#    This should be for those not setting out Apexchards using the attributes.
SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        key = "year",
        name = "Year Total",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT
    ),
    NovafosSensorDescription(
        key = "month",
        name = "Month Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT
    ),
    NovafosSensorDescription(
        key = "day",
        name = "Day Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT
    ),
    NovafosSensorDescription(
        key = "hour",
        name = "Hour",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT
    ),
    NovafosSensorDescription(
        key = "valid_date",
        name = "Valid Date for data",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = None,
        device_class = DEVICE_CLASS_DATE,
        icon = "mdi:calendar",
        state_class = STATE_CLASS_MEASUREMENT
    )
)