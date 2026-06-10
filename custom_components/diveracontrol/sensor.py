"""Definition of Home Assistant Sensors for the DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import DiveraCoordinator
from .sensor_entity import (
    DiveraAlarmSensorManager,
    DiveraAvailabilitySensorManager,
    DiveraLastAlarmSensor,
    DiveraOpenAlarmsSensor,
    DiveraUnitSensor,
    DiveraUserSensor,
    DiveraVehicleSensorManager,
)
from .utils import get_cluster_coordinators_ucrs_from_config_hass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Divera sensors."""

    _, coordinators, ucrs = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )
    ucrs: list[DiveraCoordinator] = list(coordinators.values())

    static_sensors = []

    for ucr in ucrs:
        # Create manager helpers that handle dynamic sensors
        alarm_manager = DiveraAlarmSensorManager(ucr, async_add_entities)
        vehicle_manager = DiveraVehicleSensorManager(ucr, async_add_entities)
        availability_manager = DiveraAvailabilitySensorManager(ucr, async_add_entities)

        # Start managers (they register listeners and create dynamic entities)
        alarm_manager.start()
        vehicle_manager.start()
        availability_manager.start()

        # Ensure managers are stopped when the config entry is unloaded
        config_entry.async_on_unload(alarm_manager.stop)
        config_entry.async_on_unload(vehicle_manager.stop)
        config_entry.async_on_unload(availability_manager.stop)

        static_sensors = [
            DiveraOpenAlarmsSensor(ucr),
            DiveraLastAlarmSensor(ucr),
            DiveraUnitSensor(ucr),
            DiveraUserSensor(ucr),
        ]
        async_add_entities(static_sensors)
