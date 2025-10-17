"""Definition of Home Assistant Sensors for the DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_UCR_ID
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
    ucr_id: str = config_entry.data[D_UCR_ID]
    coordinator = config_entry.runtime_data

    # Create manager helpers that handle dynamic sensors
    alarm_manager = DiveraAlarmSensorManager(coordinator, ucr_id, async_add_entities)
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

    # Add static sensors
    static_sensors = [
        DiveraOpenAlarmsSensor(coordinator, ucr_id),
        DiveraUnitSensor(coordinator, ucr_id),
    ]
    async_add_entities(static_sensors)
