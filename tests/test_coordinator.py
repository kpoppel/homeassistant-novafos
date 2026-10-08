"""Statistics import tests for the Novafos coordinator."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest

from homeassistant.components.recorder import statistics as recorder_statistics
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import valid_statistic_id
from homeassistant.components.sensor import SensorStateClass

from custom_components.novafos import coordinator as coordinator_module
from custom_components.novafos import legacy_statistics
from custom_components.novafos import update_listener
from custom_components.novafos.config_flow import OptionsFlowHandler
from custom_components.novafos.const import DOMAIN
from custom_components.novafos.const import (
    HEATING_SENSOR_TYPES,
    EXTRA_HEATING_SENSOR_TYPES,
)
from custom_components.novafos.coordinator import (
    NovafosUpdateCoordinator,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "options", "legacy", "external"),
    [
        ({"use_grouped_sensors": True}, {}, True, True),
        (
            {"use_grouped_sensors": True},
            {"use_external_statistics": False},
            True,
            False,
        ),
        (
            {"use_grouped_sensors": False},
            {"use_external_statistics": True},
            False,
            True,
        ),
        ({"use_grouped_sensors": True}, {"use_grouped_sensors": False}, False, True),
        (
            {"use_grouped_sensors": False, "use_external_statistics": False},
            {},
            False,
            False,
        ),
    ],
)
async def test_statistics_options_are_independent(
    data, options, legacy, external, monkeypatch
):
    async def run_executor(function, *args):
        return function(*args)

    api = Mock()
    api.authenticate_using_access_token.return_value = True
    api.get_year_data.return_value = {}
    api._meter_data = {}
    import_grouped = AsyncMock()
    monkeypatch.setattr(
        coordinator_module, "async_import_grouped_statistics", import_grouped
    )
    coordinator = SimpleNamespace(
        hass=SimpleNamespace(async_add_executor_job=run_executor),
        api=api,
        entry=SimpleNamespace(data=data, options=options),
        access_token="",
        access_token_date_updated="",
        _insert_statistics=AsyncMock(),
        _insert_external_hourly_statistics=AsyncMock(),
    )

    await NovafosUpdateCoordinator._async_update_data(coordinator)

    coordinator._insert_statistics.assert_awaited_once()
    assert import_grouped.await_count == int(legacy)
    assert coordinator._insert_external_hourly_statistics.await_count == int(external)


@pytest.mark.asyncio
async def test_configure_preserves_token_when_changing_statistics_options():
    entry = SimpleNamespace(
        data={"use_grouped_sensors": True},
        options={
            "access_token": "saved-token",
            "access_token_date_updated": "2026-09-01T00:00:00",
        },
    )
    flow = OptionsFlowHandler(entry)
    flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)
    flow.async_create_entry = Mock(side_effect=lambda **kwargs: kwargs)

    form = await flow.async_step_init()
    defaults = form["data_schema"]({})
    assert defaults["use_grouped_sensors"] is True
    assert defaults["use_external_statistics"] is True

    result = await flow.async_step_init(
        {**defaults, "use_grouped_sensors": False, "use_external_statistics": True}
    )
    assert result["data"]["access_token"] == "saved-token"
    assert result["data"]["access_token_date_updated"] == "2026-09-01T00:00:00"


@pytest.mark.asyncio
async def test_legacy_option_reloads_entities_external_option_refreshes():
    coordinator = SimpleNamespace(
        use_grouped_sensors=True,
        async_request_refresh=AsyncMock(),
    )
    hass = SimpleNamespace(
        data={DOMAIN: {"entry-id": {"coordinator": coordinator}}},
        config_entries=SimpleNamespace(async_reload=AsyncMock()),
    )
    entry = SimpleNamespace(
        entry_id="entry-id",
        data={"use_grouped_sensors": True},
        options={"use_external_statistics": False},
    )
    await update_listener(hass, entry)
    coordinator.async_request_refresh.assert_awaited_once()
    hass.config_entries.async_reload.assert_not_awaited()

    entry.options["use_grouped_sensors"] = False
    await update_listener(hass, entry)
    hass.config_entries.async_reload.assert_awaited_once_with("entry-id")


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
    monkeypatch.setattr(legacy_statistics, "async_import_statistics", import_statistics)

    await NovafosUpdateCoordinator._insert_statistics(coordinator, debug=False)
    await legacy_statistics.async_import_grouped_statistics(
        hass, api, grouping=("day",)
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


@pytest.mark.asyncio
@pytest.mark.parametrize("meter_types", [("heating", "water"), ("water", "heating")])
@pytest.mark.parametrize("history", ["new", "existing", "mixed", "missing_sum"])
async def test_statistics_fetches_once_and_preserves_meter_history(
    monkeypatch, freezer, meter_types, history
):
    freezer.move_to("2026-10-08T12:00:00")

    async def run_executor(function, *args):
        return function(*args)

    api = Mock()
    api.get_meter_types.return_value = [
        {"type": meter_type} for meter_type in meter_types
    ]
    api.get_available_time_series_periods.return_value = datetime(2026, 10, 5)
    api.get_statistics.return_value = {
        meter_type: [
            {
                "DateFrom": f"2026-10-{day:02d}T00:00:00",
                "Value": 20.0 if meter_type == "heating" else 0.3,
            }
            for day in (5, 6, 7)
        ]
        for meter_type in meter_types
    }
    hass = SimpleNamespace(
        async_add_executor_job=run_executor,
        config=SimpleNamespace(time_zone="Europe/Copenhagen"),
    )
    coordinator = SimpleNamespace(hass=hass, api=api)

    def last_statistics(hass, count, statistic_id, hourly, types):
        meter_type = "water" if "water" in statistic_id else "heating"
        if history == "new" or (history == "mixed" and meter_type == "heating"):
            return {}
        start = datetime(2026, 10, 7 if meter_type == "water" else 6)
        return {
            statistic_id: [
                {
                    "start": start.timestamp(),
                    "end": (start + timedelta(hours=1)).timestamp(),
                }
            ]
        }

    def statistics_history(hass, start, end, ids, period, units, types):
        statistic_id = next(iter(ids))
        if history == "missing_sum" and "water" in statistic_id:
            return {}
        return {statistic_id: [{"sum": 10.0 if "water" in statistic_id else 100.0}]}

    monkeypatch.setattr(
        coordinator_module,
        "get_instance",
        Mock(return_value=SimpleNamespace(async_add_executor_job=run_executor)),
    )
    monkeypatch.setattr(coordinator_module, "get_last_statistics", last_statistics)
    monkeypatch.setattr(
        coordinator_module, "statistics_during_period", statistics_history
    )
    import_statistics = Mock()
    monkeypatch.setattr(
        coordinator_module, "async_import_statistics", import_statistics
    )

    await NovafosUpdateCoordinator._insert_statistics(coordinator, debug=False)

    api.get_statistics.assert_called_once_with(
        datetime(2026, 1, 1) if history == "missing_sum" else datetime(2026, 10, 5)
    )
    assert import_statistics.call_count == 2
    imports = {
        call.args[1]["statistic_id"]: (call.args[1], call.args[2])
        for call in import_statistics.call_args_list
    }
    for meter_type in meter_types:
        metadata, rows = imports[f"sensor.novafos_{meter_type}_statistics"]
        existing = history != "new" and not (
            (history == "mixed" and meter_type == "heating")
            or (history == "missing_sum" and meter_type == "water")
        )
        expected_days = [6, 7] if existing and meter_type == "water" else [5, 6, 7]
        value = 0.3 if meter_type == "water" else 20.0
        baseline = (10.0 if meter_type == "water" else 100.0) if existing else 0.0
        assert [row["start"].day for row in rows] == expected_days
        assert [row["state"] for row in rows] == [value] * len(expected_days)
        assert [row["sum"] for row in rows] == pytest.approx(
            [baseline + value * index for index in range(1, len(expected_days) + 1)]
        )
        assert metadata["unit_of_measurement"] == (
            "m³" if meter_type == "water" else "kWh"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("day", "hour_count"),
    [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25)],
)
async def test_external_hourly_statistics_backfill_handles_dst(
    monkeypatch, day, hour_count
):
    async def run_executor(function, *args):
        return function(*args)

    timezone_local = ZoneInfo("Europe/Copenhagen")
    day_start = datetime.combine(day, datetime.min.time(), timezone_local)
    next_day_start = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), timezone_local
    )
    start_utc = day_start.astimezone(timezone.utc)
    next_start_utc = next_day_start.astimezone(timezone.utc)
    assert (next_start_utc - start_utc) == timedelta(hours=hour_count)

    def hourly_rows(value):
        return [
            {
                "start": (start_utc + timedelta(hours=hour)).timestamp(),
                "state": value,
                "sum": round((hour + 1) * value, 3),
            }
            for hour in range(hour_count)
        ]

    history = {
        "sensor.novafos_water_statistics": hourly_rows(0.1),
        "sensor.novafos_heating_statistics": hourly_rows(2.0)[:-1],
    }
    hass = SimpleNamespace(config=SimpleNamespace(time_zone="Europe/Copenhagen"))
    api = Mock()
    api.get_meter_types.return_value = [{"type": "water"}, {"type": "heating"}]
    coordinator = SimpleNamespace(hass=hass, api=api)
    monkeypatch.setattr(
        coordinator_module,
        "get_instance",
        Mock(return_value=SimpleNamespace(async_add_executor_job=run_executor)),
    )
    monkeypatch.setattr(
        coordinator_module,
        "get_last_statistics",
        Mock(return_value={}),
    )
    query = Mock(
        side_effect=lambda hass, start, end, ids, period, units, types: {
            statistic_id: history[statistic_id] for statistic_id in ids
        }
    )
    monkeypatch.setattr(coordinator_module, "statistics_during_period", query)
    recorder = Mock()
    monkeypatch.setattr(
        recorder_statistics, "get_instance", Mock(return_value=recorder)
    )
    monkeypatch.setattr(
        coordinator_module,
        "async_add_external_statistics",
        recorder_statistics.async_add_external_statistics,
    )

    await NovafosUpdateCoordinator._insert_external_hourly_statistics(coordinator)

    assert recorder.async_import_statistics.call_count == 2
    metadata, rows = recorder.async_import_statistics.call_args_list[0].args[:2]
    assert valid_statistic_id(metadata["statistic_id"])
    assert metadata["statistic_id"] == "novafos:water_hourly_consumption"
    assert metadata["source"] == "novafos"
    assert metadata["mean_type"] is StatisticMeanType.ARITHMETIC
    assert metadata["has_sum"] is True
    assert metadata["unit_class"] == "volume"
    assert len(rows) == hour_count
    assert rows[0] == {
        "start": start_utc,
        "min": 0.1,
        "max": 0.1,
        "mean": 0.1,
        "sum": 0.1,
    }
    assert rows[-1]["start"] == next_start_utc - timedelta(hours=1)
    assert rows[-1]["sum"] == round(hour_count * 0.1, 3)
    heating_metadata, heating_rows = recorder.async_import_statistics.call_args_list[
        1
    ].args[:2]
    assert heating_metadata["statistic_id"] == "novafos:heating_hourly_consumption"
    assert len(heating_rows) == hour_count - 1
    assert query.call_args_list[0].args[1].year == 1970
    assert all(call.args[4] == "hour" for call in query.call_args_list)


@pytest.mark.asyncio
async def test_external_hourly_statistics_recorder_roundtrip(
    async_setup_recorder_instance, hass
):
    recorder = await async_setup_recorder_instance(hass)
    start = datetime(2026, 9, 21, tzinfo=ZoneInfo(hass.config.time_zone)).astimezone(
        timezone.utc
    )
    hourly_id = "sensor.novafos_water_statistics"
    statistic_id = "novafos:water_hourly_consumption"
    hourly_metadata = StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=None,
        source="recorder",
        statistic_id=hourly_id,
        unit_class="volume",
        unit_of_measurement="m³",
    )
    recorder_statistics.async_import_statistics(
        hass,
        hourly_metadata,
        [
            StatisticData(
                start=start + timedelta(hours=hour),
                state=1.0 if hour < 24 else 2.0,
                sum=hour + 1 if hour < 24 else 24 + (hour - 23) * 2,
            )
            for hour in range(48)
        ],
    )
    await hass.async_add_executor_job(recorder.block_till_done)

    api = Mock()
    api.authenticate_using_access_token.return_value = False
    api.get_dummy_data.return_value = {}
    coordinator = SimpleNamespace(
        hass=hass,
        api=api,
        entry=SimpleNamespace(data={"use_grouped_sensors": True}, options={}),
        access_token="",
        access_token_date_updated="",
    )

    async def insert_external():
        await NovafosUpdateCoordinator._insert_external_hourly_statistics(coordinator)

    coordinator._insert_external_hourly_statistics = insert_external
    await NovafosUpdateCoordinator._async_update_data(coordinator)
    await hass.async_add_executor_job(recorder.block_till_done)
    api.get_meter_types.assert_not_called()
    api.get_statistics.assert_not_called()

    result = await hass.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        None,
        {statistic_id},
        "week",
        None,
        {"min", "mean", "max", "sum"},
    )
    assert result[statistic_id][0]["min"] == 1.0
    assert result[statistic_id][0]["mean"] == 1.5
    assert result[statistic_id][0]["max"] == 2.0
    assert result[statistic_id][0]["sum"] == 72.0

    for period in ("week", "month", "year"):
        aggregate = await hass.async_add_executor_job(
            recorder_statistics.statistics_during_period,
            hass,
            start,
            None,
            {statistic_id},
            period,
            None,
            {"min", "mean", "max", "sum", "change"},
        )
        assert len(aggregate[statistic_id]) == 1
        assert aggregate[statistic_id][0]["min"] == 1.0
        assert aggregate[statistic_id][0]["mean"] == 1.5
        assert aggregate[statistic_id][0]["max"] == 2.0
        assert aggregate[statistic_id][0]["sum"] == 72.0
        assert aggregate[statistic_id][0]["change"] == 72.0

    hourly = await hass.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        None,
        {statistic_id},
        "hour",
        None,
        {"min", "mean", "max", "sum"},
    )
    assert len(hourly[statistic_id]) == 48
    assert hourly[statistic_id][0]["min"] == 1.0
    assert hourly[statistic_id][-1]["max"] == 2.0
    assert hourly[statistic_id][-1]["sum"] == 72.0

    daily = await hass.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        None,
        {statistic_id},
        "day",
        None,
        {"min", "mean", "max", "sum", "change"},
    )
    assert [row["min"] for row in daily[statistic_id]] == [1.0, 2.0]
    assert [row["mean"] for row in daily[statistic_id]] == [1.0, 2.0]
    assert [row["max"] for row in daily[statistic_id]] == [1.0, 2.0]
    assert [row["sum"] for row in daily[statistic_id]] == [24.0, 72.0]
    assert [row["change"] for row in daily[statistic_id]] == [24.0, 48.0]
    assert daily[statistic_id][1]["change"] == 48.0

    recorder_statistics.async_import_statistics(
        hass,
        hourly_metadata,
        [StatisticData(start=start + timedelta(hours=47), state=2.5, sum=72.5)],
    )
    await hass.async_add_executor_job(recorder.block_till_done)
    await NovafosUpdateCoordinator._insert_external_hourly_statistics(coordinator)
    await hass.async_add_executor_job(recorder.block_till_done)
    corrected = await hass.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        None,
        {statistic_id},
        "week",
        None,
        {"min", "mean", "max", "sum"},
    )
    assert len(corrected[statistic_id]) == 1
    assert corrected[statistic_id][0]["min"] == 1.0
    assert corrected[statistic_id][0]["mean"] == pytest.approx(72.5 / 48)
    assert corrected[statistic_id][0]["max"] == 2.5
    assert corrected[statistic_id][0]["sum"] == 72.5


@pytest.mark.asyncio
async def test_external_consumption_trends_across_calendar_boundaries(
    async_setup_recorder_instance, hass
):
    recorder = await async_setup_recorder_instance(hass)
    start = datetime(2023, 12, 31, tzinfo=ZoneInfo(hass.config.time_zone)).astimezone(
        timezone.utc
    )
    hourly_id = "sensor.novafos_water_statistics"
    statistic_id = "novafos:water_hourly_consumption"
    recorder_statistics.async_import_statistics(
        hass,
        StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=None,
            source="recorder",
            statistic_id=hourly_id,
            unit_class="volume",
            unit_of_measurement="m³",
        ),
        [
            StatisticData(
                start=start + timedelta(hours=hour),
                state=1.0 if hour < 24 else 2.0,
                sum=hour + 1 if hour < 24 else 24 + (hour - 23) * 2,
            )
            for hour in range(48)
        ],
    )
    await hass.async_add_executor_job(recorder.block_till_done)
    coordinator = SimpleNamespace(hass=hass)
    await NovafosUpdateCoordinator._insert_external_hourly_statistics(coordinator)
    await hass.async_add_executor_job(recorder.block_till_done)

    for period in ("day", "week", "month", "year"):
        result = await hass.async_add_executor_job(
            recorder_statistics.statistics_during_period,
            hass,
            start,
            None,
            {statistic_id},
            period,
            None,
            {"change"},
        )
        assert [row["change"] for row in result[statistic_id]] == [24.0, 48.0]
