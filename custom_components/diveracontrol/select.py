"""Select platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .select_entity import DiveraUserStatusSelect, DiveraVehicleStatusSelect
from .utils import get_cluster_coordinators_ucrs_from_config_hass


def _ensure_enabled(
    hass: HomeAssistant,
    unique_ids: list[str],
) -> None:
    """Re-enable registry entries previously disabled by the integration.

    If a select entity was registered while its registry entry was disabled
    (e.g. disabled by INTEGRATION after a failed setup or migration), the
    disabled state persists across reloads. Re-enable such entries so the
    user status select is always created active. Entries disabled by the
    user are deliberately left untouched.
    """
    registry = er.async_get(hass)
    for unique_id in unique_ids:
        entry = registry.async_get_entity_id("select", "diveracontrol", unique_id)
        if entry is None:
            continue
        entity_entry = registry.async_get(entry)
        if (
            entity_entry is not None
            and entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
        ):
            registry.async_update_entity(entity_entry.entity_id, disabled_by=None)


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
    _ensure_enabled(
        hass,
        [f"{coordinator.ucr_id}_user_status" for coordinator in coordinators.values()],
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
