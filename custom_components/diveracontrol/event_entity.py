"""Support for Divera event entities."""

from typing import Any

from homeassistant.components.event import EventEntity

from .const import (
    D_ALARM,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
)
from .coordinator import DiveraCoordinator
from .entity import BaseDiveraEntity


class DiveraAlarmFeedEvent(BaseDiveraEntity, EventEntity):
    """Static event entity per device summarizing all alarm lifecycle events.

    This entity exists from setup on, before any alarm has arrived, so it is
    always selectable as an automation trigger target for the device.
    It fires "opened", "updated" and "closed" events carrying the alarm data
    of the affected alarm as event attributes.
    """

    _attr_event_types = ["opened", "updated", "closed"]
    _attr_translation_key = "alarm_feed"
    _attr_entity_registry_visible_default = False

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init class DiveraAlarmFeedEvent."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self.ucr_id}_alarm_feed"
        self.entity_id = f"event.{self.ucr_id}_alarm_feed"
        self._known_alarm_ids: set[str] = set()
        self._closed_alarm_ids: set[str] = set()
        self._last_alarm_data: dict[str, dict[str, Any]] = {}

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available

    @property
    def icon(self) -> str:
        """Return the icon of the alarm feed."""
        return I_OPEN_ALARM_NOPRIO

    def _handle_coordinator_update(self) -> None:
        """Fire events for all alarms changed since the last update."""
        super()._handle_coordinator_update()
        alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
        current_ids = set(alarm_items.keys())

        for alarm_id in current_ids - self._known_alarm_ids:
            alarm_details = alarm_items[alarm_id]
            self._known_alarm_ids.add(alarm_id)
            if alarm_details.get("closed", False):
                self._closed_alarm_ids.add(alarm_id)
                continue
            self._last_alarm_data[alarm_id] = dict(alarm_details)
            self._trigger_event("opened", alarm_details)

        for alarm_id in self._known_alarm_ids & current_ids:
            alarm_details = alarm_items[alarm_id]
            if alarm_id not in self._closed_alarm_ids:
                if alarm_details.get("closed", False):
                    self._closed_alarm_ids.add(alarm_id)
                    self._trigger_event("closed", alarm_details)
                elif alarm_details != self._last_alarm_data.get(alarm_id):
                    self._trigger_event("updated", alarm_details)
                    self._last_alarm_data[alarm_id] = dict(alarm_details)

        self._last_alarm_data = {
            alarm_id: dict(alarm_items[alarm_id])
            for alarm_id in current_ids & self._known_alarm_ids
            if not alarm_items[alarm_id].get("closed", False)
        }


class DiveraAlarmEvent(BaseDiveraEntity, EventEntity):
    """Event entity to represent a single alarm."""

    _attr_event_types = ["opened", "updated", "closed"]

    _attr_translation_key = "alarm"

    _fired_initial_event: bool = False
    _fired_closed_event: bool = False

    def __init__(self, coordinator: DiveraCoordinator, alarm_id: str) -> None:
        """Init class DiveraAlarmEvent."""
        super().__init__(coordinator)

        self.alarm_id = alarm_id

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{self.ucr_id}_alarm_{self.alarm_id}"
        self.entity_id = f"event.{self.ucr_id}_alarm_{self.alarm_id}"

    def _get_alarm_data(self) -> dict[str, Any] | None:
        """Get alarm data safely, return None if alarm doesn't exist."""
        alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
        return alarm_items.get(self.alarm_id)

    @property
    def name(self) -> str:
        """Return name of the alarm (the alarm title)."""
        if alarm_data := self._get_alarm_data():
            return str(alarm_data.get("title", "Unknown"))
        return "Unknown Alarm"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if super().available and self._get_alarm_data() is not None:
            return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the alarm."""
        if alarm_data := self._get_alarm_data():
            return {"alarm_id": self.alarm_id, **alarm_data}
        return {}

    @property
    def icon(self) -> str:
        """Return the icon of the alarm."""
        if alarm_data := self._get_alarm_data():
            _closed = alarm_data.get("closed", False)
            _priority = alarm_data.get("priority", False)
            return (
                I_CLOSED_ALARM
                if _closed
                else I_OPEN_ALARM if _priority else I_OPEN_ALARM_NOPRIO
            )
        return I_OPEN_ALARM_NOPRIO

    async def async_added_to_hass(self) -> None:
        """Fire the initial event when the entity is added.

        A newly created alarm entity has no restored state and fires its
        "opened" event immediately, so it never shows up as unknown.
        After a restart the restored state exists and no "opened" event
        is fired again for already known alarms.
        """
        await super().async_added_to_hass()
        alarm_data = self._get_alarm_data()
        if alarm_data is None:
            return
        self._fired_initial_event = True
        last_state = await self.async_get_last_state()
        if last_state is None:
            self._trigger_event("opened", alarm_data)
        elif alarm_data.get("closed", False):
            self._fired_closed_event = True

    def _handle_coordinator_update(self) -> None:
        """Fire events on alarm lifecycle transitions.

        - "opened": once, when the alarm first appears
        - "closed": once, when the alarm changes from open to closed
        """
        alarm_data = self._get_alarm_data()
        if alarm_data is None:
            super()._handle_coordinator_update()
            return

        if not self._fired_initial_event:
            self._fired_initial_event = True
            self._trigger_event("opened", alarm_data)
        elif not self._fired_closed_event and alarm_data.get("closed", False):
            self._fired_closed_event = True
            self._trigger_event("closed", alarm_data)
        super()._handle_coordinator_update()
