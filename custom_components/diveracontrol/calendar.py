"""Manage calendar for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .calendar_entity import DiveraCalendar
from .const import D_CLUSTER_ID, D_COORDINATOR, DOMAIN
from .coordinator import DiveraCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable[[list], None],  # type: ignore[no-untyped-call]
) -> None:
    """Set up the Divera calendar entity."""
    cluster_id = str(config_entry.data.get(D_CLUSTER_ID, ""))
    coordinator_data = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)
    coordinators: list[DiveraCoordinator] = list(coordinator_data.values())

    calendar_entities = [DiveraCalendar(coordinator) for coordinator in coordinators]
    async_add_entities(calendar_entities)
