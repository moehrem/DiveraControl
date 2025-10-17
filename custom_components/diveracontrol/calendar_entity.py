"""Support for Divera Control calendar events."""

from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import parse_datetime, utc_from_timestamp

from .const import D_EVENTS
from .coordinator import DiveraCoordinator
from .utils import get_device_info

_LOGGER = logging.getLogger(__name__)


class DiveraCalendar(CoordinatorEntity, CalendarEntity):
    """A single calendar entity for all Divera events."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DiveraCoordinator, ucr_id: str) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator)

        self.ucr_id = ucr_id
        self._attr_device_info = get_device_info(coordinator.cluster_name)
        self._attr_unique_id = f"{ucr_id}_calendar"
        self.entity_id = f"calendar.{ucr_id}_calendar"

        self._event_list: list[dict[str, Any]] = []

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        event_items: dict[str, Any] = self.coordinator.data.get(D_EVENTS, {}).get(
            "items", {}
        )

        self.update_events(event_items)
        self.async_write_ha_state()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self._event_list:
            return None

        now = datetime.now(UTC)

        # Filter future events only and parse datetimes
        upcoming_events = []
        for e in self._event_list:
            event_start = parse_datetime(e["start"]["dateTime"])
            if event_start and event_start >= now:
                upcoming_events.append((e, event_start))

        if not upcoming_events:
            return None

        # Sort by start time
        sorted_events = sorted(upcoming_events, key=lambda x: x[1])
        first_event, start = sorted_events[0]

        end = parse_datetime(first_event["end"]["dateTime"])

        if not start or not end:
            _LOGGER.warning("Invalid datetime in event: %s", first_event)
            return None

        return CalendarEvent(
            start=start,
            end=end,
            summary=first_event["summary"],
            description=first_event.get("description", ""),
            location=first_event.get("location"),
        )

    def update_events(self, event_items: dict[str, Any]) -> None:
        """Update the event list with new data."""
        self._event_list = []

        for event_id, event_data in event_items.items():
            start_ts = event_data.get("start", 0)
            end_ts = event_data.get("end", 0)

            if start_ts == 0 or end_ts == 0:
                _LOGGER.debug("Skipping event %s with invalid timestamps", event_id)
                continue

            start = utc_from_timestamp(start_ts)
            end = utc_from_timestamp(end_ts)

            self._event_list.append(
                {
                    "start": {"dateTime": start.isoformat()},
                    "end": {"dateTime": end.isoformat()},
                    "summary": event_data.get("title", "Kein Titel"),
                    "description": event_data.get("text", ""),
                    "location": event_data.get("address", ""),
                    "all_day": event_data.get("fullday", False),
                }
            )

        _LOGGER.debug(
            "Updated calendar %s with %d events",
            self.ucr_id,
            len(self._event_list),
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        _LOGGER.debug(
            "Fetching events from %s to %s for %s",
            start_date,
            end_date,
            self.ucr_id,
        )

        events: list[CalendarEvent] = []
        for event in self._event_list:
            event_start = parse_datetime(event["start"]["dateTime"])
            event_end = parse_datetime(event["end"]["dateTime"])

            if not event_start or not event_end:
                continue

            # Check if event overlaps with requested range
            if event_start < end_date and event_end > start_date:
                events.append(
                    CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=event["summary"],
                        description=event.get("description", ""),
                        location=event.get("location"),
                    )
                )

        _LOGGER.debug("Returning %d events for range", len(events))
        return events
