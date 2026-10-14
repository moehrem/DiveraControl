"""Event platform for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DiveraCoordinator
from .const import D_ALARM, DOMAIN
from .event_entity import DiveraAlarmEvent
from .utils import get_cluster_coordinators_ucrs_from_config_hass


class DiveraAlarmEventManager:
    """Manage dynamic event entities for open alarms.

    Manages the lifecycle (add/remove) of alarm event entities whose set of
    IDs changes at runtime, mirroring the behavior of
    ``DiveraSensorManager`` for the event platform.
    """

    def __init__(
        self,
        coordinator: DiveraCoordinator,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the alarm event manager."""
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._ucr_id = coordinator.ucr_id
        self._async_add_entities = async_add_entities
        self._known_ids: set[str] = set()
        self._unsub: Callable[[], None] | None = None

    def start(self) -> None:
        """Register coordinator listener and run an initial update."""
        if self._unsub is not None:
            return
        self._unsub = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        self._handle_coordinator_update()

    def stop(self) -> None:
        """Unregister coordinator listener."""
        if self._unsub:
            try:
                self._unsub()
            finally:
                self._unsub = None

    def _handle_coordinator_update(self) -> None:
        """Sync known entities with the current data from the coordinator.

        Alarms stay available as events until Divera archives them (removes
        them from the alarm items, at the latest 90 days after creation).
        Closed alarms therefore remain visible as closed alarms.
        """
        alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
        current_ids = set(alarm_items.keys())

        removed_ids = self._known_ids - current_ids
        if removed_ids:
            entity_registry = er.async_get(self.hass)
            for alarm_id in removed_ids:
                unique_id = f"{self._ucr_id}_alarm_{alarm_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "event", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
            self._known_ids.difference_update(removed_ids)

        new_ids = current_ids - self._known_ids
        if new_ids:
            new_entities = [
                DiveraAlarmEvent(self.coordinator, alarm_id) for alarm_id in new_ids
            ]
            self._async_add_entities(new_entities, update_before_add=False)
            self._known_ids.update(new_ids)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Divera event entities."""
    _, coordinators, _ = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )
    for coordinator in coordinators.values():
        alarm_event_manager = DiveraAlarmEventManager(coordinator, async_add_entities)
        alarm_event_manager.start()
        config_entry.async_on_unload(alarm_event_manager.stop)
