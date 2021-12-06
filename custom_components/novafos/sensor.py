"""Platform for Eloverblik sensor integration."""
import logging
from homeassistant.const import (VOLUME_CUBIC_METERS, DEVICE_CLASS_GAS)
from homeassistant.components.sensor import (SensorEntity, STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL,
                                            STATE_CLASS_TOTAL_INCREASING)
#from homeassistant.helpers.entity import Entity
from custom_components.novafos.pynovafos.novafos import Novafos
from custom_components.novafos.pynovafos.models import TimeSeries

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN



async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    novafos = hass.data[DOMAIN][config.entry_id]

    sensors = []
    sensors.append(NovafosWater("Novafos Water Total", 'total', novafos))
    for x in range(1, 25):
        sensors.append(NovafosWater(f"Novafos Water {x-1}-{x}", 'hour', novafos, x))
    async_add_entities(sensors)


class NovafosWater(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, name, sensor_type, client, hour=None):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client
        self._hour = hour
        self._sensor_type = sensor_type

        self._attr_name = name


        if sensor_type == 'hour':
            self._attr_unique_id = f"{self._data.get_metering_point()}-{hour}"
        else:
            self._attr_unique_id = f"{self._data.get_metering_point()}-total"

        self._attr_native_unit_of_measurement = VOLUME_CUBIC_METERS
        self._attr_icon = "mdi:water"
        self._attr_state_class = STATE_CLASS_MEASUREMENT #STATE_CLASS_TOTAL
        # Only gas can be measured in m3
        self._attr_device_class = DEVICE_CLASS_GAS

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        attributes['metering_date'] = self._data_date
        return attributes

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(f"Setting status for {self._attr_name}")
        self._data.update()

        self._data_date = self._data.get_data_date()

        if self._sensor_type == 'total':
            self._attr_native_value = self._data.get_year_to_date()
        else:
            self._attr_native_value = self._data.get_usage_hour(self._hour)
        _LOGGER.debug(f"Setting status for {self._attr_name} = {self._attr_native_value} {self._attr_native_unit_of_measurement}")

