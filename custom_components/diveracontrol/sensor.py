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

    # Create manager entities that handle dynamic sensors
    alarm_manager = DiveraAlarmSensorManager(coordinator, ucr_id, async_add_entities)
    vehicle_manager = DiveraVehicleSensorManager(
        coordinator, ucr_id, async_add_entities
    )
    availability_manager = DiveraAvailabilitySensorManager(
        coordinator, ucr_id, async_add_entities
    )

    # Add managers first (they will create dynamic entities)
    async_add_entities([alarm_manager, vehicle_manager, availability_manager])

    # Add static sensors
    static_sensors = [
        DiveraOpenAlarmsSensor(coordinator, ucr_id),
        DiveraUnitSensor(coordinator, ucr_id),
    ]
    async_add_entities(static_sensors)
