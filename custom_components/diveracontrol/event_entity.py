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


class DiveraAlarmEvent(BaseDiveraEntity, EventEntity):
    """Event entity to represent a single alarm."""

    _attr_event_types = ["triggered", "updated", "closed"]

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
    def available(self) -> bool:
        """Return if entity is available."""
        if super().available and self._get_alarm_data() is not None:
            return True
        return False

    @property
    def name(self) -> str:
        """Return name of the alarm."""
        if alarm_data := self._get_alarm_data():
            return str(alarm_data.get("title", "Unknown"))
        return "Unknown Alarm"

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

    def _handle_coordinator_update(self) -> None:
        """Fire events on alarm lifecycle transitions.

        - "triggered": once, when the alarm first appears
        - "closed": once, when the alarm changes from open to closed
        """
        alarm_data = self._get_alarm_data()
        if alarm_data is None:
            super()._handle_coordinator_update()
            return

        if not self._fired_initial_event:
            self._fired_initial_event = True
            self._trigger_event("triggered", alarm_data)
        elif not self._fired_closed_event and alarm_data.get("closed", False):
            self._fired_closed_event = True
            self._trigger_event("closed", alarm_data)
        super()._handle_coordinator_update()
