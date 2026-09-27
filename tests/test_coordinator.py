"""Statistics import tests for the Novafos coordinator."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorStateClass

from custom_components.novafos import coordinator as coordinator_module
from custom_components.novafos.const import (
    HEATING_SENSOR_TYPES,
    EXTRA_HEATING_SENSOR_TYPES,
)
from custom_components.novafos.coordinator import NovafosUpdateCoordinator


@pytest.mark.asyncio
async def test_import_statistics_with_existing_sum_only_history(monkeypatch):
    async def run_executor(function, *args):
        return function(*args)

    api = Mock()
    api.get_meter_types.return_value = [{"type": "water"}, {"type": "heating"}]
    api.get_statistics.return_value = {
        "water": [{"DateFrom": "2026-09-26T00:00:00", "Value": 0.5}],
        "heating": [{"DateFrom": "2026-09-26T00:00:00", "Value": 2.0}],
    }
    api.get_grouped_statistics.side_effect = lambda meter_type, grouping: [
        (
            "2026-09-26T00:00:00",
            10.0 if meter_type == "water" else 30.0,
            0.5,
            0.0,
            0.5,
            0.25,
        )
    ]
    hass = SimpleNamespace(
        async_add_executor_job=run_executor,
        config=SimpleNamespace(time_zone="Europe/Copenhagen"),
    )
    coordinator = SimpleNamespace(hass=hass, api=api)
    monkeypatch.setattr(
        coordinator_module,
        "get_instance",
        Mock(return_value=SimpleNamespace(async_add_executor_job=run_executor)),
    )
    monkeypatch.setattr(
        coordinator_module,
        "get_last_statistics",
        Mock(
            return_value={
                "sensor.novafos_water_statistics": [
                    {"start": 1790380800, "end": 1790384400}
                ],
                "sensor.novafos_heating_statistics": [
                    {"start": 1790380800, "end": 1790384400}
                ],
            }
        ),
    )
    monkeypatch.setattr(
        coordinator_module,
        "statistics_during_period",
        Mock(
            return_value={
                "sensor.novafos_water_statistics": [{"sum": 12.0}],
                "sensor.novafos_heating_statistics": [{"sum": 20.0}],
            }
        ),
    )
    import_statistics = Mock()
    monkeypatch.setattr(
        coordinator_module, "async_import_statistics", import_statistics
    )

    await NovafosUpdateCoordinator._insert_statistics(coordinator, debug=False)
    await NovafosUpdateCoordinator._insert_grouped_statistics(
        coordinator, grouping=("day",)
    )

    imports = {
        call.args[1]["statistic_id"]: (call.args[1], call.args[2])
        for call in import_statistics.call_args_list
    }
    for statistic_id in (
        "sensor.novafos_water_statistics",
        "sensor.novafos_water_statistics_day",
    ):
        metadata, statistics = imports[statistic_id]
        assert metadata["mean_type"] is StatisticMeanType.NONE
        assert metadata["unit_class"] == "volume"
        assert metadata["has_sum"] is True
        assert "mean" not in statistics[0]
        assert "max" not in statistics[0]
        assert "min" not in statistics[0]
    assert imports["sensor.novafos_water_statistics"][1][0]["sum"] == 12.5

    for statistic_id in (
        "sensor.novafos_heating_statistics",
        "sensor.novafos_heating_statistics_day",
    ):
        metadata, statistics = imports[statistic_id]
        assert metadata["mean_type"] is StatisticMeanType.NONE
        assert metadata["unit_class"] == "energy"
        assert metadata["has_sum"] is True
        assert "mean" not in statistics[0]
        assert "max" not in statistics[0]
        assert "min" not in statistics[0]
    assert imports["sensor.novafos_heating_statistics"][1][0]["sum"] == 22.0
    assert imports["sensor.novafos_heating_statistics_day"][1][0]["sum"] == 30.0
    assert all(
        description.state_class is SensorStateClass.TOTAL
        for description in HEATING_SENSOR_TYPES + EXTRA_HEATING_SENSOR_TYPES
    )
