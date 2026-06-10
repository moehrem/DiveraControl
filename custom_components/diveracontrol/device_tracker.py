"""Device tracker platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import DiveraCoordinator
from .device_tracker_entity import (
    DiveraAlarmTrackerManager,
    DiveraVehicleTrackerManager,
)
from .utils import get_cluster_coordinators_ucrs_from_config_hass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Divera device trackers."""

    _, coordinators, ucrs = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )
    ucrs: list[DiveraCoordinator] = list(coordinators.values())

    for ucr in ucrs:
        # Create manager helpers that handle dynamic trackers
        alarm_tracker_manager = DiveraAlarmTrackerManager(ucr, async_add_entities)
        vehicle_tracker_manager = DiveraVehicleTrackerManager(ucr, async_add_entities)

        # Start managers (they register listeners and create dynamic trackers)
        alarm_tracker_manager.start()
        vehicle_tracker_manager.start()

        # Ensure managers are stopped when the config entry is unloaded
        config_entry.async_on_unload(alarm_tracker_manager.stop)
        config_entry.async_on_unload(vehicle_tracker_manager.stop)
