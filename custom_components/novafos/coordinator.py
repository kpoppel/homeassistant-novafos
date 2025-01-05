"""DataUpdateCoordinator for Novafos."""
from __future__ import annotations

from custom_components.novafos.pynovafos.novafos import Novafos
#from .sensor import NovafosWaterSensor

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import HomeAssistantError

from datetime import datetime as dt
from datetime import timedelta
from random import randrange

from .const import MIN_TIME_BETWEEN_UPDATES

from pprint import pformat
import logging
_LOGGER = logging.getLogger(__name__)
import random

#### New for statistics ####
from .const import DOMAIN
from homeassistant.components.recorder import DOMAIN as RECORDER_DOMAIN, get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
    async_import_statistics
)
from homeassistant.util import dt as dt_util
from homeassistant.const import UnitOfVolume, UnitOfEnergy
from typing import cast
#### TO HERE ####

class NovafosUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator for Novafos."""
    def __init__(
        self,
        hass: HomeAssistant,
        api: Novafos,
        entry: ConfigEntry,
    ) -> None:
        """Initialize DataUpdateCoordinator"""
        self.api = api
        self.hass = hass
        self.entry = entry
        self.supplierid = entry.data['supplierid']
        # Need local version here to enable updating via action service calls
        self.access_token = self.entry.options['access_token']
        self.access_token_date_updated = self.entry.options['access_token_date_updated']
        
        # Set last time we updated to right now.
        self.last_update = dt.now()
        
        super().__init__(
            hass,
            _LOGGER,
            name="Novafos"
        )

    async def _async_update_data(self):
        """ Get the data for Novafos. """
        _LOGGER.debug(f"Performing token based authentication")
        if await self.hass.async_add_executor_job(self.api.authenticate_using_access_token, self.access_token, self.access_token_date_updated):
            # Retrieve latest data from the API
            try:
                _LOGGER.debug("Getting latest data")
                data = await self.hass.async_add_executor_job(self.api.get_latest)
                #_LOGGER.debug(pformat(data))
                # Check last
                _LOGGER.debug("Getting latest statistics")
                await self._insert_statistics()
            except Exception as error:
                raise ConfigEntryNotReady from error
        else:
            data = self.api.get_dummy_data()

        # TEMP:
        #data = self.api.get_dummy_data()
        # Return the data
        # The data is stored in the coordinator as a .data field.
        return data

    async def _insert_statistics(self) -> None:
        """ Update statistics when data is returned """
        # Iterate over water/heating
        # self.api.get_meters() -- do something with that. and so on
        # [{'type': 'water', 'InstallationId': 16496761, 'MeasurementPointId': 16639137, 'Unit': {'Id': 10319, 'Name': 'm³', 'Description': 'Vand', 'Decimals': 0, 'Order': 1}}]
        for meter_device in self.api.get_meter_types():
            meter_type = meter_device['type']
            _LOGGER.debug("Retrieving statistics data for %s meter.", meter_type)

            statistic_id = f"sensor.{DOMAIN}_{meter_type}_statistics"
            if meter_type == "water":
                unit = UnitOfVolume.CUBIC_METERS
            else:
                unit = UnitOfEnergy.KILOWATT_HOUR

            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, statistic_id, True, set()
            )
            # Returns: last_stats = defaultdict(<class 'list'>, {'sensor.novafos_water_statistics': [{'start': 1735948800.0, 'end': 1735952400.0}]})
            if not last_stats:
                # First time we insert 365 days of data (if available)
                one_year_back = dt.now().replace(year=dt.now().year-1, month=1, day=1, hour=0, minute=0, second=0)
                _LOGGER.debug("No last statistics detected - retrieving data since %s.", one_year_back)
                data = await self.hass.async_add_executor_job(self.api.get_statistics, one_year_back)
                _sum = 0.0
                #last_stats_time = None
            else:
                # Fetch data since last statistics updated
                _LOGGER.debug(f"Last statistics: {dt.fromtimestamp(last_stats[statistic_id][0]['start'])}-{dt.fromtimestamp(last_stats[statistic_id][0]['end'])}")
                # TODO: Retrieve data fixed 10 days before last statistics update - could be set to just get since the last data point.
                # TODO: correct sum and last_stats_time
                start = dt.fromtimestamp(last_stats[statistic_id][0]['end'])
                stat = await get_instance(self.hass).async_add_executor_job(
                    statistics_during_period,
                    self.hass,
                    start,
                    None,
                    {statistic_id},
                    "hour",
                    None,
                    {"sum"},
                )
                # Returns: defaultdict(<class 'list'>, {'sensor.novafos_water_statistics': [{'start': 1736031600.0, 'end': 1736035200.0, 'sum': 134.73000000000002}]})
                _LOGGER.debug(f"Statistics in period: {stat}")
                data = await self.hass.async_add_executor_job(self.api.get_statistics, start-timedelta(days=100))
                if statistic_id in stat:
                    _sum = cast(float, stat[statistic_id][0]['sum'])
                else:
                    # For some reason the latest statistics has nothing? Panic and get data 1 year back again!
                    one_year_back = dt.now().replace(year=dt.now().year-1, month=1, day=1, hour=0, minute=0, second=0)
                    _LOGGER.debug("No last statistics detected - retrieving data since %s.", one_year_back)
                    data = await self.hass.async_add_executor_job(self.api.get_statistics, one_year_back)
                    _sum = 0.0

            # Array of statistics points
            statistics = []

            # Populate statistics array
            for val in data[meter_type]:
                # Add timezone to dataset as Home Assistant works in UTC
                from_time = dt_util.parse_datetime(f"{val["DateFrom"]}").replace(tzinfo=dt_util.get_time_zone(self.hass.config.time_zone))
                _LOGGER.debug(f"Adding: {from_time}, {val["Value"]}")
                _sum += val["Value"]

                statistics.append(
                    StatisticData(
                        start=from_time,
                        state=val["Value"],
                        sum=_sum,
                    )
                )

            if False:
                hourly_data = self.tst_data()

                #tz = await dt_util.async_get_time_zone()
                #_LOGGER.debug(tz)
                # Update hourly data
                for data in hourly_data['Series'][0]['Data']:
                    from_time = dt_util.parse_datetime(data["DateFrom"])
                    #_LOGGER.debug(f"{from_time}, {data["Value"]}")
                    if from_time is None or (
                        last_stats_time_dt is not None
                        and from_time <= last_stats_time_dt
                    ):
                        continue

                    _sum += data["Value"]

                    statistics.append(
                        StatisticData(
                            start=from_time,
                            state=data["Value"],
                            sum=_sum,
                        )
                    )
                    if data["UnitName"] == "kWh":
                        unit = UnitOfEnergy.KILO_WATT_HOUR
                    else:
                        unit = UnitOfVolume.CUBIC_METERS

            # For min/max/average check out https://github.com/emontnemery/home-assistant/blob/dev/homeassistant/components/kitchen_sink/__init__.py#L148,
            # https://github.com/emontnemery/home-assistant/blob/dev/homeassistant/components/recorder/models/statistics.py#L31
            # metadata = StatisticMetaData(
            #     has_mean=False,
            #     has_sum=True,
            #     name=f"Novafos {meter_type} Statistics",
            #     source=DOMAIN,
            #     statistic_id=statistic_id,
            #     unit_of_measurement=unit,
            # )
            # Creates a new statictics "novafos:<name>".  This is different from the sensor.<name>
            #async_add_external_statistics(self.hass, metadata, statistics)    

            # Apexchart does not understand the domain:statistic noation, so we'll use an internal sensor instead.
            # Update the sensor statistics.  Only the hourly one is needed as the sensor can then aggregate data itself.
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name= None,
                source=RECORDER_DOMAIN,
                statistic_id="sensor.novafos_water_statistics",
                unit_of_measurement=unit,
            )
            async_import_statistics(self.hass, metadata, statistics)

    def tst_data(self):
        # Generate fake data
        data = []
        first_day = dt_util.parse_datetime("2024-01-02T00:00:00+01:00")
        for day in range(1, 366):
            for hour in range(0,24):
                # "2025-01-02T00:00:00+01:00"
                stamp = first_day + timedelta(hours=hour)
                data.append({
                                "DateFrom": stamp.strftime("%Y-%m-%dT%H:00:00+01:00"),
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                })
            first_day = first_day + timedelta(days=1)
        #_LOGGER.debug(data)
        return {
                "Average": {
                    "DateFrom": "2025-01-02T00:00:00",
                    "DateTo": "2025-01-02T23:59:59",
                    "Value": 0.015
                },
                "Maximum": {
                    "DateFrom": "2025-01-02T11:00:00",
                    "DateTo": "2025-01-02T11:59:59",
                    "Value": 0.216
                },
                "Minimum": {
                    "DateFrom": "2025-01-02T02:00:00",
                    "DateTo": "2025-01-02T02:59:59",
                    "Value": 0.0
                },
                "Series": [
                            { "Data": data,
                              "Label": None
                            }
                        ],
                "SheetName": None,
                "Total": {
                    "DateFrom": "2025-01-02T00:00:00+01:00",
                    "DateTo": "2025-01-02T23:59:59+01:00",
                    "Value": 0.354
                }
            }
        return {
                "Average": {
                    "DateFrom": "2025-01-02T00:00:00",
                    "DateTo": "2025-01-02T23:59:59",
                    "Value": 0.015
                },
                "Maximum": {
                    "DateFrom": "2025-01-02T11:00:00",
                    "DateTo": "2025-01-02T11:59:59",
                    "Value": 0.216
                },
                "Minimum": {
                    "DateFrom": "2025-01-02T02:00:00",
                    "DateTo": "2025-01-02T02:59:59",
                    "Value": 0.0
                },
                "Series": [
                    {
                        "Data": [
                            {
                                "DateFrom": "2025-01-02T00:00:00+01:00",
                                "DateTo": "2025-01-02T00:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T01:00:00+01:00",
                                "DateTo": "2025-01-02T01:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T02:00:00+01:00",
                                "DateTo": "2025-01-02T02:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T03:00:00+01:00",
                                "DateTo": "2025-01-02T03:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T04:00:00+01:00",
                                "DateTo": "2025-01-02T04:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T05:00:00+01:00",
                                "DateTo": "2025-01-02T05:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T06:00:00+01:00",
                                "DateTo": "2025-01-02T06:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T07:00:00+01:00",
                                "DateTo": "2025-01-02T07:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T08:00:00+01:00",
                                "DateTo": "2025-01-02T08:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T09:00:00+01:00",
                                "DateTo": "2025-01-02T09:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T10:00:00+01:00",
                                "DateTo": "2025-01-02T10:59:59+01:00",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T11:00:00+01:00",
                                "DateTo": "2025-01-02T11:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T12:00:00+01:00",
                                "DateTo": "2025-01-02T12:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T13:00:00+01:00",
                                "DateTo": "2025-01-02T13:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T14:00:00+01:00",
                                "DateTo": "2025-01-02T14:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T15:00:00+01:00",
                                "DateTo": "2025-01-02T15:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T16:00:00+01:00",
                                "DateTo": "2025-01-02T16:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T17:00:00+01:00",
                                "DateTo": "2025-01-02T17:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T18:00:00+01:00",
                                "DateTo": "2025-01-02T18:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T19:00:00+01:00",
                                "DateTo": "2025-01-02T19:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T20:00:00+01:00",
                                "DateTo": "2025-01-02T20:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T21:00:00+01:00",
                                "DateTo": "2025-01-02T21:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T22:00:00+01:00",
                                "DateTo": "2025-01-02T22:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            },
                            {
                                "DateFrom": "2025-01-02T23:00:00+01:00",
                                "DateTo": "2025-01-02T23:59:59",
                                "IsComplete": True,
                                "IsSettlement": False,
                                "Label": "",
                                "UnitName": "m³",
                                "Value": random.randint(0,25)
                            }
                        ],
                        "Label": None
                    }
                ],
                "SheetName": None,
                "Total": {
                    "DateFrom": "2025-01-02T00:00:00+01:00",
                    "DateTo": "2025-01-02T23:59:59+01:00",
                    "Value": 0.354
                }
            }

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""