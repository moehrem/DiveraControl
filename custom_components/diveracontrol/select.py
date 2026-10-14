"""Select platform for DiveraControl integration."""

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import D_CLUSTER, D_VEHICLE, DOMAIN
from .divera_permissions import DiveraPermissions
from .select_entity import DiveraUserStatusSelect, DiveraVehicleStatusSelect
from .sensor_entity import DiveraSensorManager
from .utils import get_cluster_coordinators_ucrs_from_config_hass

_LOGGER = logging.getLogger(__name__)


def _coordinator_permissions(coordinator) -> DiveraPermissions:
    """Return the coordinator's permission handler, tolerating mocks."""
    permissions = getattr(getattr(coordinator, "api", None), "permissions", None)
    if isinstance(permissions, DiveraPermissions):
        return permissions
    return DiveraPermissions()


def DiveraVehicleSelectManager(  # pylint: disable=invalid-name
    coordinator,
    async_add_entities,
) -> DiveraSensorManager:
    """Create a DiveraSensorManager pre-configured for vehicle selects.

    Only vehicles the user may write the FMS status for are exposed as
    select entities; other vehicles get a read-only sensor instead.
    """
    return DiveraSensorManager(
        coordinator=coordinator,
        async_add_entities=async_add_entities,
        get_current_ids=lambda data: {
            item_id
            for item_id in data.get(D_CLUSTER, {}).get(D_VEHICLE, {}).keys()
            if _coordinator_permissions(coordinator).can_write_vehicle_status(
                item_id
            )
        },
        build_unique_id=lambda ucr_id, item_id: f"{ucr_id}_vehicle_status_{item_id}",
        entity_factory=DiveraVehicleStatusSelect,
        label="vehicle select",
        domain="select",
    )


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


def _remove_stale_user_status_select(
    hass: HomeAssistant,
    unique_id: str,
) -> None:
    """Remove a user status select registry entry after a permission loss.

    When the Divera permission to set the user status is revoked, the
    formerly writable select is replaced by a read-only sensor. The old
    select registry entry must be removed explicitly so no orphan remains.
    """
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("select", DOMAIN, unique_id)
    if entity_id:
        registry.async_remove(entity_id)
        _LOGGER.info(
            "Removed user status select %s: write permission no longer granted",
            entity_id,
        )


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
        if _coordinator_permissions(coordinator).can_write_user_status():
            user_status_entities = [DiveraUserStatusSelect(coordinator)]
            async_add_entities(
                user_status_entities,
                update_before_add=False,
            )
        else:
            _LOGGER.info(
                "User '%s' (ucr %s) may not set the user status in Divera, "
                "creating a read-only sensor instead",
                coordinator.user_name,
                coordinator.ucr_id,
            )
            _remove_stale_user_status_select(
                hass, f"{coordinator.ucr_id}_user_status"
            )

        vehicle_manager = DiveraVehicleSelectManager(coordinator, async_add_entities)
        vehicle_manager.start()
        config_entry.async_on_unload(vehicle_manager.stop)
