"""Definition of Home Assistant Sensors for the DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import DiveraCoordinator
from .sensor_entity import (
    DiveraAvailabilitySensorManager,
    DiveraLastAlarmSensor,
    DiveraOpenAlarmsSensor,
    DiveraUnitSensor,
    DiveraUserSensor,
    DiveraUserStatusSensorManager,
    DiveraVehicleStatusSensorManager,
)
from .utils import get_cluster_coordinators_ucrs_from_config_hass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Divera sensors."""

    _, coordinators, _ = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )
    ucrs: list[DiveraCoordinator] = list(coordinators.values())

    static_sensors = []

    for ucr in ucrs:
        # Create manager helpers that handle dynamic sensors
        availability_manager = DiveraAvailabilitySensorManager(ucr, async_add_entities)
        vehicle_status_sensor_manager = DiveraVehicleStatusSensorManager(
            ucr, async_add_entities
        )
        user_status_sensor_manager = DiveraUserStatusSensorManager(
            ucr, async_add_entities
        )

        # Start managers (they register listeners and create dynamic entities)
        availability_manager.start()
        vehicle_status_sensor_manager.start()
        user_status_sensor_manager.start()

        # Ensure managers are stopped when the config entry is unloaded
        config_entry.async_on_unload(availability_manager.stop)
        config_entry.async_on_unload(vehicle_status_sensor_manager.stop)
        config_entry.async_on_unload(user_status_sensor_manager.stop)

        static_sensors = [
            DiveraOpenAlarmsSensor(ucr),
            DiveraLastAlarmSensor(ucr),
            DiveraUnitSensor(ucr),
            DiveraUserSensor(ucr),
        ]
        async_add_entities(static_sensors)
