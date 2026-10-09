"""Select platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .select_entity import DiveraUserStatusSelect, DiveraVehicleStatusSelect
from .utils import get_cluster_coordinators_ucrs_from_config_hass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Divera select entities."""
    # cluster_id = str(config_entry.data.get(D_CLUSTER_ID, ""))
    # coordinators = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)
    # ucrs: list[DiveraCoordinator] = list(coordinators.values())
    _, coordinators, _ = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )
    for coordinator in coordinators.values():
        user_status_entities = [DiveraUserStatusSelect(coordinator)]
        async_add_entities(
            user_status_entities,
            update_before_add=False,
        )

        vehicles: dict = coordinator.data.get("cluster", {}).get("vehicle", {})
        vehicle_entities = [
            DiveraVehicleStatusSelect(coordinator, str(vehicle_id))
            for vehicle_id in vehicles
        ]
        if vehicle_entities:
            async_add_entities(
                vehicle_entities,
                update_before_add=False,
            )
