"""DataUpdateCoordinator for Novafos."""

from __future__ import annotations

# If debugging, use pre-seeded data:
# from .pynovafos.sample_data import (
#     get_active_meters,
#     get_year_sample_data,
#     get_year_sample_data_extra,
# )
import logging
from datetime import datetime as dt
from datetime import timedelta
from typing import cast

from homeassistant.components.recorder import DOMAIN as RECORDER_DOMAIN
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    async_import_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, meter_statistics_key
from .legacy_statistics import async_import_grouped_statistics
from .pynovafos.novafos import Novafos

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
        self.use_grouped_sensors = entry.options.get(
            "use_grouped_sensors", entry.data.get("use_grouped_sensors", False)
        )
        # Attribute data for the sensors
        self.attrib_data = {"year_total": None}
        # Need local version here to enable updating via action service calls
        self.access_token = self.entry.options.get("access_token", "")
        self.access_token_date_updated = self.entry.options.get(
            "access_token_date_updated", ""
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

        meter_year_data = None
        hourly_statistics = None
        if await self.hass.async_add_executor_job(
            self.api.authenticate_using_access_token,
            self.access_token,
            self.access_token_date_updated,
        ):
            # Retrieve latest data from the API
            # if True:
            try:
                _LOGGER.debug("Getting latest statistics")
                meter_year_data = await self.hass.async_add_executor_job(
                    self.api.get_year_data
                )
                # last_state = await self._insert_statistics(debug=debug)
                hourly_statistics = await self._insert_statistics(debug=debug)
                if self.entry.options.get(
                    "use_grouped_sensors",
                    self.entry.data.get("use_grouped_sensors", False),
                ):
                    await async_import_grouped_statistics(
                        self.hass, self.api, entry_data=self.entry.data
                    )
                data = (self.api._meter_data, meter_year_data)  # , last_state)
            except Exception as ex:
                raise UpdateFailed(f"The service is unavailable: {ex}")
        else:
            meter_type = self.entry.data.get("meter_type")
            dummy_data = (
                self.api.get_dummy_data(meter_type)
                if meter_type
                else self.api.get_dummy_data()
            )
            data = (dummy_data, meter_year_data)

        if self.entry.options.get(
            "use_external_statistics",
            self.entry.data.get("use_external_statistics", True),
        ):
            await self._insert_external_hourly_statistics(hourly_statistics)

        # The data is stored in the coordinator as a .data field.
        _LOGGER.debug("Returning from Coordinator with data: %s", data)
        return data

    async def _insert_statistics(self, debug) -> dict[str, list[StatisticData]]:
        """Update statistics when data is returned"""
        hourly_statistics = {}
        meter_statistics = []
        min_date = None
        # Iterate over water/heating
        # _get_meter_types returns:
        #      [{'type': 'water', 'InstallationId': 12345678, 'MeasurementPointId': 23456789, 'Unit': {'Id': 11111, 'Name': 'm³', 'Description': 'Vand', 'Decimals': 0, 'Order': 1}}]
        for meter_device in self.api.get_meter_types():
            meter_type = meter_device["type"]
            _LOGGER.debug("Retrieving statistics data for %s meter.", meter_type)

            meter_key = meter_statistics_key(self.entry.data, meter_type)
            statistic_id = f"sensor.{DOMAIN}_{meter_key}_statistics"
            if meter_type == "water":
                unit = UnitOfVolume.CUBIC_METERS
                unit_class = "volume"
            else:
                unit = UnitOfEnergy.KILO_WATT_HOUR
                unit_class = "energy"

            # TODO: Find actual last statistics where sum is not zero??
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, statistic_id, True, set()
            )
            # Returns: last_stats = defaultdict(<class 'list'>, {'sensor.novafos_water_statistics': [{'start': 1735948800.0, 'end': 1735952400.0}]})
            _LOGGER.debug("Last statistics (raw): %s", last_stats)
            if not last_stats:
                # First time we insert 365 days of data (if available)
                if min_date is None:
                    min_date = await self.hass.async_add_executor_job(
                        self.api.get_available_time_series_periods
                    )

                one_year_back = dt.now().replace(
                    year=dt.now().year - 1,
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                )

                # Don't go back further than the available data:
                one_year_back = max(one_year_back, min_date)

                _LOGGER.debug(
                    "No last statistics detected - retrieving data since %s. Your earliest data is from %s. This could take a while.",
                    one_year_back,
                    min_date,
                )
                start = one_year_back
                _sum = 0.0
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
                    {"sum"},
                )
                # Returns: defaultdict(<class 'list'>, {'sensor.novafos_water_statistics': [{'start': 1736031600.0, 'end': 1736035200.0, 'sum': 134.73000000000002}]})
                _LOGGER.debug(f"Statistics in period: {stat}")

                if statistic_id in stat:
                    _sum = cast(float, stat[statistic_id][0]["sum"])
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
                    start = one_year_back
                    # Need to reset sum to 0.0 because we don't know the offset any more.
                    _sum = 0.0

            meter_statistics.append(
                (meter_type, statistic_id, unit, unit_class, start, _sum)
            )

        if not meter_statistics:
            return hourly_statistics

        if debug:
            data = self.api._meter_data
        else:
            data = await self.hass.async_add_executor_job(
                self.api.get_statistics,
                min(statistics[4] for statistics in meter_statistics),
            )

        for meter_type, statistic_id, unit, unit_class, start, _sum in meter_statistics:
            # Array of statistics points
            statistics = []

            # Populate statistics array
            for val in data[meter_type]:
                # Add timezone to dataset as Home Assistant works in UTC
                from_time = dt_util.parse_datetime(f"{val['DateFrom']}").replace(
                    tzinfo=dt_util.get_time_zone(self.hass.config.time_zone)
                )
                if from_time.date() < start.date():
                    continue
                _sum += val["Value"]
                # _LOGGER.debug(f"Adding: {from_time}, {val["Value"]}, {_sum}")

                statistics.append(
                    StatisticData(
                        start=from_time,
                        state=val["Value"],
                        sum=_sum,
                    )
                )

            # For min/max/average check out https://github.com/emontnemery/home-assistant/blob/dev/homeassistant/components/kitchen_sink/__init__.py#L148,
            # https://github.com/emontnemery/home-assistant/blob/dev/homeassistant/components/recorder/models/statistics.py#L31
            # metadata = StatisticMetaData(
            #     mean_type=StatisticMeanType.ARITHMETIC,
            #     has_sum=True,
            #     name=f"Novafos {meter_type} Statistics",
            #     source=DOMAIN,
            #     statistic_id=statistic_id,
            #     unit_of_measurement=unit,
            # )
            # Creates a new statistics "novafos:<name>".  This is different from the sensor.<name>
            # async_add_external_statistics(self.hass, metadata, statistics)

            # Apexchart does not understand the domain:statistic notation, so we'll use an internal sensor instead.
            # Update the sensor statistics.  Only the hourly one is needed as the sensor can then aggregate data itself.
            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=None,
                source=RECORDER_DOMAIN,
                statistic_id=statistic_id,
                unit_class=unit_class,
                unit_of_measurement=unit,
            )
            async_import_statistics(self.hass, metadata, statistics)
            hourly_statistics[meter_type] = statistics

            # Could return last state for a sensor - but the sensor state ruins the statistics.
            # return statistics[-1]['state']

        return hourly_statistics

    async def _insert_external_hourly_statistics(
        self, hourly_statistics: dict[str, list[StatisticData]] | None = None
    ) -> None:
        """Import fetched hourly data and backfill older recorded statistics."""
        recorder = get_instance(self.hass)
        for meter_type in ("water", "heating"):
            if self.entry.data.get("meter_type", meter_type) != meter_type:
                continue
            fetched = (hourly_statistics or {}).get(meter_type, [])
            meter_key = meter_statistics_key(self.entry.data, meter_type)
            statistic_id = f"{DOMAIN}:{meter_key}_hourly_consumption"
            hourly_id = f"sensor.{DOMAIN}_{meter_key}_statistics"
            last_stats = await recorder.async_add_executor_job(
                get_last_statistics, self.hass, 1, statistic_id, True, {"sum"}
            )
            last_statistic = last_stats.get(statistic_id, [])
            last_start = last_statistic[0].get("start") if last_statistic else None
            start = (
                dt.fromtimestamp(last_start, dt_util.UTC) - timedelta(days=10)
                if last_start is not None
                else dt(1970, 1, 1, tzinfo=dt_util.UTC)
            )
            history = await recorder.async_add_executor_job(
                statistics_during_period,
                self.hass,
                start,
                min(row["start"] for row in fetched) if fetched else None,
                {hourly_id},
                "hour",
                None,
                {"state", "sum"},
            )
            statistics = []
            for row in history.get(hourly_id, []):
                value = row.get("state")
                timestamp = row.get("start")
                running_sum = row.get("sum")
                if value is None or timestamp is None or running_sum is None:
                    continue
                statistics.append(
                    StatisticData(
                        start=dt.fromtimestamp(timestamp, dt_util.UTC),
                        min=value,
                        max=value,
                        mean=value,
                        sum=running_sum,
                    )
                )

            for row in fetched:
                value = row.get("state")
                running_sum = row.get("sum")
                if value is None or running_sum is None:
                    continue
                statistics.append(
                    StatisticData(
                        start=dt_util.as_utc(row["start"]),
                        min=value,
                        max=value,
                        mean=value,
                        sum=running_sum,
                    )
                )

            if statistics:
                is_water = meter_type == "water"
                metadata = StatisticMetaData(
                    mean_type=StatisticMeanType.ARITHMETIC,
                    has_sum=True,
                    name=(
                        f"Novafos {self.entry.data['address']} {meter_type} hourly consumption"
                        if self.entry.data.get("address")
                        else f"Novafos {meter_type} hourly consumption"
                    ),
                    source=DOMAIN,
                    statistic_id=statistic_id,
                    unit_class="volume" if is_water else "energy",
                    unit_of_measurement=(
                        UnitOfVolume.CUBIC_METERS
                        if is_water
                        else UnitOfEnergy.KILO_WATT_HOUR
                    ),
                )
                async_add_external_statistics(self.hass, metadata, statistics)


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
