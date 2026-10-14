"""Fire alarm lifecycle events on the Home Assistant event bus.

This module tracks the alarm items of one coordinator and fires an event of
type ``ALARM_EVENT_TYPE`` on the Home Assistant event bus whenever an alarm
is opened, updated or closed. The events carry the device id, ucr id, the
alarm id and the full alarm data, so automations can react to them via
device triggers without any event entity.
"""

from collections.abc import Callable
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import (
    ALARM_EVENT_TYPE,
    ATTR_ALARM_DATA,
    ATTR_ALARM_EVENT_TYPE,
    ATTR_ALARM_ID,
    D_ALARM,
    DOMAIN,
)
from .coordinator import DiveraCoordinator

_LOGGER = logging.getLogger(__name__)


class DiveraAlarmEventBusManager:
    """Fire alarm lifecycle transitions as events on the event bus."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DiveraCoordinator,
    ) -> None:
        """Initialize the alarm event bus manager."""
        self.hass = hass
        self.coordinator = coordinator
        self._ucr_id = coordinator.ucr_id
        self._known_alarm_ids: set[str] = set()
        self._closed_alarm_ids: set[str] = set()
        self._last_alarm_data: dict[str, dict] = {}
        self._device_id: str | None = None
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

    def _get_device_id(self) -> str | None:
        """Return the device id of the ucr device."""
        if self._device_id is not None:
            return self._device_id
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, self._ucr_id)})
        if device is not None:
            self._device_id = device.id
        return self._device_id

    def _fire_event(self, event_type: str, alarm_id: str, alarm_data: dict) -> None:
        """Fire an alarm lifecycle event on the event bus."""
        device_id = self._get_device_id()
        if device_id is None:
            _LOGGER.debug(
                "No device found for ucr %s, skipping alarm event",
                self._ucr_id,
            )
            return
        self.hass.bus.async_fire(
            ALARM_EVENT_TYPE,
            {
                "device_id": device_id,
                ATTR_ALARM_EVENT_TYPE: event_type,
                ATTR_ALARM_ID: alarm_id,
                ATTR_ALARM_DATA: dict(alarm_data),
            },
        )

    def _fire_derived_event(self, event_type: str) -> None:
        """Fire a derived alarm event on the event bus."""
        device_id = self._get_device_id()
        if device_id is None:
            _LOGGER.debug(
                "No device found for ucr %s, skipping alarm event",
                self._ucr_id,
            )
            return
        self.hass.bus.async_fire(
            ALARM_EVENT_TYPE,
            {
                "device_id": device_id,
                ATTR_ALARM_EVENT_TYPE: event_type,
            },
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire events for all alarms changed since the last update."""
        alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
        current_ids = set(alarm_items.keys())

        had_open_alarms = bool(self._known_alarm_ids - self._closed_alarm_ids)

        for alarm_id in current_ids - self._known_alarm_ids:
            alarm_details = alarm_items[alarm_id]
            self._known_alarm_ids.add(alarm_id)
            if alarm_details.get("closed", False):
                self._closed_alarm_ids.add(alarm_id)
                continue
            self._last_alarm_data[alarm_id] = dict(alarm_details)
            self._fire_event("opened", alarm_id, alarm_details)

        for alarm_id in self._known_alarm_ids & current_ids:
            alarm_details = alarm_items[alarm_id]
            if alarm_id not in self._closed_alarm_ids:
                if alarm_details.get("closed", False):
                    self._closed_alarm_ids.add(alarm_id)
                    self._fire_event("closed", alarm_id, alarm_details)
                elif alarm_details != self._last_alarm_data.get(alarm_id):
                    self._last_alarm_data[alarm_id] = dict(alarm_details)
                    self._fire_event("updated", alarm_id, alarm_details)

        has_open_alarms = bool(self._known_alarm_ids - self._closed_alarm_ids)
        if had_open_alarms and not has_open_alarms:
            self._fire_derived_event("all_alarms_closed")
