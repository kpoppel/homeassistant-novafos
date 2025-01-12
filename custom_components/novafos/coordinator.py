"""DataUpdateCoordinator for Novafos."""

from __future__ import annotations

from .pynovafos.novafos import Novafos

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import HomeAssistantError

from datetime import datetime as dt
from datetime import timedelta


from .const import DOMAIN
from homeassistant.components.recorder import DOMAIN as RECORDER_DOMAIN, get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    get_last_statistics,
    statistics_during_period,
    async_import_statistics,
)
from homeassistant.util import dt as dt_util
from homeassistant.const import UnitOfVolume, UnitOfEnergy
from typing import cast

# If debugging, use pre-seeded data:
# from .pynovafos.sample_data import (
#     get_active_meters,
#     get_year_sample_data,
#     get_year_sample_data_extra,
# )

import logging

_LOGGER = logging.getLogger(__name__)


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
        # Need local version here to enable updating via action service calls
        self.access_token = (
            self.entry.options["access_token"]
            if "access_token" in self.entry.options
            else ""
        )
        self.access_token_date_updated = (
            self.entry.options["access_token_date_updated"]
            if "access_token_date_updated" in self.entry.options
            else ""
        )

        super().__init__(hass, _LOGGER, name="Novafos")

    async def _async_update_data(self):
        """Get the data for Novafos."""
        _LOGGER.debug("Performing token based authentication")

        debug = False
        # If debugging and need to re-seed the database:
        # if debug:
        #     # Pre-seed data from file
        #     self.api._active_meters = get_active_meters()
        #     self.api._meter_data = get_year_sample_data()
        #     self.api._meter_data_extra = get_year_sample_data_extra()

        if await self.hass.async_add_executor_job(
            self.api.authenticate_using_access_token,
            self.access_token,
            self.access_token_date_updated,
        ):
            # Retrieve latest data from the API
            try:
                _LOGGER.debug("Getting latest statistics")
                await self._insert_statistics(debug)
                await self._insert_grouped_statistics(debug)
                data = self.api._meter_data
            except Exception as ex:
                raise UpdateFailed(f"The service is unavailable: {ex}")
        else:
            data = self.api.get_dummy_data()

        # The data is stored in the coordinator as a .data field.
        _LOGGER.debug("Returning from Coordinator with data: %s", data)
        return data

    async def _insert_statistics(self, debug) -> None:
        """Update statistics when data is returned"""
        # Iterate over water/heating
        # _get_meter_types returns:
        #      [{'type': 'water', 'InstallationId': 16496761, 'MeasurementPointId': 16639137, 'Unit': {'Id': 10319, 'Name': 'm³', 'Description': 'Vand', 'Decimals': 0, 'Order': 1}}]
        for meter_device in self.api.get_meter_types():
            meter_type = meter_device["type"]
            _LOGGER.debug("Retrieving statistics data for %s meter.", meter_type)

            statistic_id = f"sensor.{DOMAIN}_{meter_type}_statistics"
            if meter_type == "water":
                unit = UnitOfVolume.CUBIC_METERS
            else:
                unit = UnitOfEnergy.KILOWATT_HOUR

            # TODO: Find actual last statistics where sum is not zero??
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, statistic_id, True, set()
            )
            # Returns: last_stats = defaultdict(<class 'list'>, {'sensor.novafos_water_statistics': [{'start': 1735948800.0, 'end': 1735952400.0}]})
            _LOGGER.debug("Last statistics (raw): %s", last_stats)
            if not last_stats:
                # First time we insert 365 days of data (if available)
                one_year_back = dt.now().replace(
                    year=dt.now().year - 1, month=1, day=1, hour=0, minute=0, second=0
                )
                _LOGGER.debug(
                    "No last statistics detected - retrieving data since %s.",
                    one_year_back,
                )
                if debug:
                    data = self.api._meter_data
                else:
                    data = await self.hass.async_add_executor_job(
                        self.api.get_statistics, one_year_back
                    )
                _sum = 0.0
                _max = data[meter_type][0]["Value"]
                _min = data[meter_type][0]["Value"]
                _mean = data[meter_type][0]["Value"]
            else:
                # Fetch data this many days back
                delta_days = 1
                # Fetch data since last statistics updated
                start = dt.fromtimestamp(
                    last_stats[statistic_id][0]["start"]
                ) - timedelta(days=delta_days)
                end = dt.fromtimestamp(last_stats[statistic_id][0]["end"])
                _LOGGER.debug(f"Last statistics: {start}-{end}")
                # TODO: Retrieve data fixed 10 days before last statistics update - could be set to just get since the last data point.
                # start = dt.fromtimestamp(last_stats[statistic_id][0]['end']) # end of last statistics point, asking for this gives no data points.
                # Retrieve stored statistics one day further back because this is where the starting sum comes from.
                stat = await get_instance(self.hass).async_add_executor_job(
                    statistics_during_period,
                    self.hass,
                    start - timedelta(days=1),
                    None,
                    {statistic_id},
                    "hour",
                    None,
                    {"sum", "max", "min", "mean"},
                )
                # Returns: defaultdict(<class 'list'>, {'sensor.novafos_water_statistics': [{'start': 1736031600.0, 'end': 1736035200.0, 'sum': 134.73000000000002}]})
                _LOGGER.debug(f"Statistics in period: {stat}")

                if debug:
                    data = self.api._meter_data
                else:
                    data = await self.hass.async_add_executor_job(
                        self.api.get_statistics, start
                    )
                if statistic_id in stat:
                    _sum = cast(float, stat[statistic_id][0]["sum"])
                    _max = cast(float, stat[statistic_id][0]["max"])
                    _min = cast(float, stat[statistic_id][0]["min"])
                    _mean = cast(float, stat[statistic_id][0]["mean"])
                else:
                    # For some reason the latest statistics has nothing? Panic and get data 1 year back again!
                    # one_year_back = dt.now().replace(year=dt.now().year-1, month=1, day=1, hour=0, minute=0, second=0)
                    # Or just get data since the start of the year:
                    one_year_back = dt.now().replace(
                        year=dt.now().year, month=1, day=1, hour=0, minute=0, second=0
                    )
                    _LOGGER.warning(
                        "No last statistics detected - this is unexpected - retrieving data since %s.",
                        one_year_back,
                    )
                    data = await self.hass.async_add_executor_job(
                        self.api.get_statistics, one_year_back
                    )
                    # Need to reset sum to 0.0 because we don't know the offset any more.
                    _sum = 0.0
                    _max = data[meter_type][0]["Value"]
                    _min = data[meter_type][0]["Value"]
                    _mean = data[meter_type][0]["Value"]

            # Array of statistics points
            statistics = []

            # Populate statistics array
            last_value = data[meter_type][0]["Value"]
            for val in data[meter_type]:
                # Add timezone to dataset as Home Assistant works in UTC
                from_time = dt_util.parse_datetime(f"{val["DateFrom"]}").replace(
                    tzinfo=dt_util.get_time_zone(self.hass.config.time_zone)
                )
                _sum += val["Value"]
                _max = last_value if val["Value"] < last_value else val["Value"]
                _min = last_value if val["Value"] >= last_value else val["Value"]
                _mean = (_min + _max) / 2
                last_value = val["Value"]
                # _LOGGER.debug(f"Adding: {from_time}, {val["Value"]}, {_sum}")

                statistics.append(
                    StatisticData(
                        start=from_time,
                        state=val["Value"],
                        sum=_sum,
                        min=_min,
                        max=_max,
                        mean=_mean,
                    )
                )

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
            # Creates a new statistics "novafos:<name>".  This is different from the sensor.<name>
            # async_add_external_statistics(self.hass, metadata, statistics)

            # Apexchart does not understand the domain:statistic noation, so we'll use an internal sensor instead.
            # Update the sensor statistics.  Only the hourly one is needed as the sensor can then aggregate data itself.
            metadata = StatisticMetaData(
                has_mean=True,
                has_sum=True,
                name=None,
                source=RECORDER_DOMAIN,
                statistic_id=statistic_id,
                unit_of_measurement=unit,
            )
            async_import_statistics(self.hass, metadata, statistics)

    async def _insert_grouped_statistics(self, debug) -> None:
        """Update statistics when data is returned"""
        # Iterate over water/heating
        # _get_meter_types returns:
        #      [{'type': 'water', 'InstallationId': 16496761, 'MeasurementPointId': 16639137, 'Unit': {'Id': 10319, 'Name': 'm³', 'Description': 'Vand', 'Decimals': 0, 'Order': 1}}]
        for meter_device in self.api.get_meter_types():
            for grouping in ["day", "week", "month", "year"]:
                meter_type = meter_device["type"]
                _LOGGER.debug(
                    "Generating grouped statistics data for %s meter for %s.",
                    meter_type,
                    grouping,
                )

                dataset = self.api.get_grouped_statistics("water", grouping)
                statistic_id = f"sensor.{DOMAIN}_{meter_type}_statistics_{grouping}"
                if meter_type == "water":
                    unit = UnitOfVolume.CUBIC_METERS
                else:
                    unit = UnitOfEnergy.KILOWATT_HOUR

                # Naive version - just recalculate the complete history of the sensor data

                # Array of statistics points
                statistics = []

                # Populate statistics array
                for date, _sum, _change, _max, _min, _mean in dataset:
                    # Add timezone to dataset as Home Assistant works in UTC
                    from_time = dt_util.parse_datetime(date).replace(
                        tzinfo=dt_util.get_time_zone(self.hass.config.time_zone)
                    )
                    # _LOGGER.debug(f"Adding: {from_time}, {val["Value"]}, {_sum}")

                    statistics.append(
                        StatisticData(
                            start=from_time,
                            state=_sum,
                            sum=_sum,
                            min=_min,
                            max=_max,
                            mean=_mean,
                        )
                    )

                metadata = StatisticMetaData(
                    has_mean=True,
                    has_sum=True,
                    name=None,
                    source=RECORDER_DOMAIN,
                    statistic_id=statistic_id,
                    unit_of_measurement=unit,
                )
                async_import_statistics(self.hass, metadata, statistics)


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
