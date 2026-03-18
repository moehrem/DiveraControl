"""Definition of Home Assistant Sensors for the DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_CLUSTER_ID, D_COORDINATOR, DOMAIN
from .coordinator import DiveraCoordinator
from .sensor_entity import (
    DiveraAlarmSensorManager,
    DiveraAvailabilitySensorManager,
    DiveraOpenAlarmsSensor,
    DiveraUnitSensor,
    DiveraVehicleSensorManager,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Divera sensors."""

    cluster_id = str(config_entry.data.get(D_CLUSTER_ID, ""))
    coordinator_data = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)

    if isinstance(coordinator_data, dict):
        coordinators: list[DiveraCoordinator] = list(coordinator_data.values())
    else:
        coordinators = [config_entry.runtime_data]

    static_sensors = []

    for coordinator in coordinators:
        ucr_id: str = coordinator.ucr_id

        # Create manager helpers that handle dynamic sensors
        alarm_manager = DiveraAlarmSensorManager(
            coordinator, ucr_id, async_add_entities
        )
        vehicle_manager = DiveraVehicleSensorManager(
            coordinator, ucr_id, async_add_entities
        )
        availability_manager = DiveraAvailabilitySensorManager(
            coordinator, ucr_id, async_add_entities
        )

        # Start managers (they register listeners and create dynamic entities)
        alarm_manager.start()
        vehicle_manager.start()
        availability_manager.start()

        # Ensure managers are stopped when the config entry is unloaded
        config_entry.async_on_unload(alarm_manager.stop)
        config_entry.async_on_unload(vehicle_manager.stop)
        config_entry.async_on_unload(availability_manager.stop)

        static_sensors.extend(
            [
                DiveraOpenAlarmsSensor(coordinator, ucr_id),
                DiveraUnitSensor(coordinator, ucr_id),
            ]
        )

    async_add_entities(static_sensors)
