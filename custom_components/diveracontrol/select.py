"""Select platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import PERM_STATUS_USER
from .select_entity import DiveraUserStatusSelect, DiveraVehicleStatusSelect
from .utils import get_cluster_coordinators_ucrs_from_config_hass


def _sync_registry_state(
    hass: HomeAssistant,
    coordinators: dict,
) -> None:
    """Sync registry disabled state of user status selects to permissions.

    The user status select is only useful if the Divera user is permitted
    to set their own status. Depending on that permission, the entity is
    created enabled or disabled (``entity_registry_enabled_default``).
    Because a registry entry persists its disabled state across reloads,
    entries previously disabled by the integration are re-enabled here
    when the permission is granted. Entries disabled by the user are
    deliberately left untouched.
    """
    registry = er.async_get(hass)
    for coordinator in coordinators.values():
        unique_id = f"{coordinator.ucr_id}_user_status"
        entry = registry.async_get_entity_id("select", "diveracontrol", unique_id)
        if entry is None:
            continue
        entity_entry = registry.async_get(entry)
        if (
            entity_entry is None
            or entity_entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION
        ):
            continue
        permitted = (
            coordinator.api is not None
            and coordinator.api.permissions.is_permitted(PERM_STATUS_USER)
        )
        if permitted:
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
    _sync_registry_state(hass, coordinators)
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
