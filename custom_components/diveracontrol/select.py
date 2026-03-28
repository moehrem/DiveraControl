"""Select platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_CLUSTER_ID, D_COORDINATOR, DOMAIN
from .coordinator import DiveraCoordinator
from .select_entity import DiveraUserStatusSelect


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Divera select entities."""

    cluster_id = str(config_entry.data.get(D_CLUSTER_ID, ""))
    coordinators = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)
    ucrs: list[DiveraCoordinator] = list(coordinators.values())

    for ucr in ucrs:
        user_status_entities = [DiveraUserStatusSelect(ucr)]
        async_add_entities(
            user_status_entities,
            update_before_add=False,
            config_subentry_id=ucr.subentry_id,
        )
