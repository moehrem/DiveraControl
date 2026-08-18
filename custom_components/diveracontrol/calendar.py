"""Manage calendar for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import _LOGGER, HomeAssistant

from .calendar_entity import DiveraCalendar
from .const import D_CLUSTER_ID, D_COORDINATOR, DOMAIN
from .coordinator import DiveraCoordinator
from .utils import get_cluster_coordinators_ucrs_from_config_hass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable[[list], None],
) -> None:
    """Set up the Divera calendar entity."""
    # cluster_id = str(config_entry.data.get(D_CLUSTER_ID, ""))
    # coordinator_data = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)
    # coordinators: list[DiveraCoordinator] = list(coordinator_data.values())

    cluster_id, coordinators, _ = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )

    calendar_entities = [
        DiveraCalendar(coordinator) for coordinator in coordinators.values()
    ]
    _LOGGER.debug(
        "Setting up %d calendar entities for cluster %s",
        len(calendar_entities),
        cluster_id,
    )
    async_add_entities(calendar_entities)
