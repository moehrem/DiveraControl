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
    coordinator_data = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)

    if isinstance(coordinator_data, dict):
        coordinators: list[DiveraCoordinator] = list(coordinator_data.values())
    else:
        coordinators = [config_entry.runtime_data]

    for coordinator in coordinators:
        ucr_id: str = coordinator.ucr_id

        # Create manager helpers that handle dynamic trackers
        alarm_tracker_manager = DiveraAlarmTrackerManager(
            coordinator, ucr_id, async_add_entities
        )
        vehicle_tracker_manager = DiveraVehicleTrackerManager(
            coordinator, ucr_id, async_add_entities
        )

        # Start managers (they register listeners and create dynamic trackers)
        alarm_tracker_manager.start()
        vehicle_tracker_manager.start()

        # Ensure managers are stopped when the config entry is unloaded
        config_entry.async_on_unload(alarm_tracker_manager.stop)
        config_entry.async_on_unload(vehicle_tracker_manager.stop)
