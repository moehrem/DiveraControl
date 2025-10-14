"""Device tracker platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_UCR_ID
from .device_tracker_entity import (
    DiveraAlarmTrackerManager,
    DiveraVehicleTrackerManager,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Divera device trackers."""
    ucr_id: str = config_entry.data[D_UCR_ID]
    coordinator = config_entry.runtime_data

    # Create manager trackers that handle dynamic entities
    alarm_tracker_manager = DiveraAlarmTrackerManager(
        coordinator, ucr_id, async_add_entities
    )
    vehicle_tracker_manager = DiveraVehicleTrackerManager(
        coordinator, ucr_id, async_add_entities
    )

    # Managers register themselves and handle updates automatically
    async_add_entities([alarm_tracker_manager, vehicle_tracker_manager])
