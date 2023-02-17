"""Constants for the Novafos integration."""
from __future__ import annotations
from typing import Final
from datetime import timedelta
# Get Sensor classification and unit definitions:
from homeassistant.components.sensor import SensorStateClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.const import UnitOfVolume

from .model import NovafosSensorDescription

DOMAIN = "novafos"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "Novafos"

######################################################################
##  NOTICE ON FAIR USE:
##  Please do not set this constant below 15 minutes.
##  You will risk an IP-ban if fair use is not adhered to.
##
##  The dataset is updated every 24 hours in the morning.
##  The default min. time is to spread out load on the API and still
##  retrieve data.
######################################################################
# NOTE: Due to reCAPTCHA login screen, automatic updates is set to a very large number
#MIN_TIME_BETWEEN_UPDATES = timedelta(days=365)
# Every 6 hours seems appropriate to get an update ready in the morning
# This number is adjusted dynamically after first fetch to only update every 24 hours when using selenium login.
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Smallest appropriate interval.  Only relevant for development use.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)

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
#    This should be for those not setting up Apexchards using the attributes.
WATER_SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        sensor_type = "water",
        key = "year",
        name = "Year Total",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL
    ),
    NovafosSensorDescription(
        sensor_type = "water",
        key = "month",
        name = "Month Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL
    ),
    NovafosSensorDescription(
        sensor_type = "water",
        key = "day",
        name = "Day Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = None
    ),
    NovafosSensorDescription(
        sensor_type = "water",
        key = "hour",
        name = "Hour",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = None
    ),
    NovafosSensorDescription(
        sensor_type = "water",
        key = "valid_date",
        name = "Valid Date for data",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = None,
        device_class = SensorDeviceClass.DATE,
        icon = "mdi:calendar",
        state_class = None
    )
)

HEATING_SENSOR_TYPES: Final[tuple[NovafosSensorDescription, ...]] = (
    NovafosSensorDescription(
        sensor_type = "heating",
        key = "year",
        name = "Heating Year Total",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL
    ),
    NovafosSensorDescription(
        sensor_type = "heating",
        key = "month",
        name = "Heating Month Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL
    ),
    NovafosSensorDescription(
        sensor_type = "heating",
        key = "day",
        name = "Heating Day Total",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = None
    ),
    NovafosSensorDescription(
        sensor_type = "heating",
        key = "hour",
        name = "Heating Hour",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = None
    ),
    NovafosSensorDescription(
        sensor_type = "heating",
        key = "valid_date",
        name = "Heating_Valid Date for data",
        entity_registry_enabled_default=True,
        native_unit_of_measurement = None,
        device_class = SensorDeviceClass.DATE,
        icon = "mdi:calendar",
        state_class = None
    )
)