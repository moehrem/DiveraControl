"""Device tracker platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_CLUSTER_ID, D_COORDINATOR, DOMAIN
from .coordinator import DiveraCoordinator
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

    cluster_id = str(config_entry.data.get(D_CLUSTER_ID, ""))
    coordinators = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)
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
