"""Deprecated grouped sensor statistics imports, retained until the next major release."""

import logging

from homeassistant.components.recorder import DOMAIN as RECORDER_DOMAIN
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.util import dt as dt_util

from .const import DOMAIN, meter_statistics_key

_LOGGER = logging.getLogger(__name__)


async def async_import_grouped_statistics(
    hass, api, grouping=("day", "week", "month", "year"), *, entry_data=None
) -> None:
    """Import statistics for the deprecated grouped sensor entities."""
    for meter_device in api.get_meter_types():
        for group in grouping:
            meter_type = meter_device["type"]
            _LOGGER.debug(
                "Generating grouped statistics data for %s meter for %s.",
                meter_type,
                group,
            )

            dataset = api.get_grouped_statistics(meter_type, group)
            meter_key = meter_statistics_key(entry_data or {}, meter_type)
            statistic_id = f"sensor.{DOMAIN}_{meter_key}_statistics_{group}"
            if meter_type == "water":
                unit = UnitOfVolume.CUBIC_METERS
                unit_class = "volume"
            else:
                unit = UnitOfEnergy.KILO_WATT_HOUR
                unit_class = "energy"

            statistics = []
            for date, total, _change, _min, _max, _mean in dataset:
                from_time = dt_util.parse_datetime(date).replace(
                    tzinfo=dt_util.get_time_zone(hass.config.time_zone)
                )
                statistics.append(
                    StatisticData(
                        start=from_time,
                        state=total,
                        sum=total,
                    )
                )

            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=None,
                source=RECORDER_DOMAIN,
                statistic_id=statistic_id,
                unit_class=unit_class,
                unit_of_measurement=unit,
            )
            async_import_statistics(hass, metadata, statistics)
