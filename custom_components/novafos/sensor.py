"""Platform for Eloverblik sensor integration."""
import logging
from homeassistant.const import VOLUME_CUBIC_METERS
from homeassistant.helpers.entity import Entity
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


class NovafosWater(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, sensor_type, client, hour=None):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client
        self._hour = hour
        self._name = name
        self._sensor_type = sensor_type

        if sensor_type == 'hour':
            self._unique_id = f"{self._data.get_metering_point()}-{hour}"
        else:
            self._unique_id = f"{self._data.get_metering_point()}-total"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """The unique id of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.debug(f"Asked for state {self._name} = {self._state}")
        return self._state

    @property
    def device_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        attributes['metering_date'] = self._data_date
        
        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return VOLUME_CUBIC_METERS

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update()        

        self._data_date = self._data.get_data_date()

        if self._sensor_type == 'total':
            self._state = self._data.get_year_to_date()
        else:
            self._state = self._data.get_usage_hour(self._hour)
        _LOGGER.debug(f"Setting status for {self._name} = {self._state} {VOLUME_CUBIC_METERS}")

