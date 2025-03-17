from datetime import datetime, timezone
import asyncio
import logging
import re
from typing import Set, Any

from homeassistant.core import HomeAssistant
from homeassistant.components.calendar import CalendarEntity, CalendarEvent

from homeassistant.util.dt import parse_datetime

from .const import DOMAIN, D_CLUSTER_ID, D_COORDINATOR, D_EVENTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Divera-Calendar entity."""
    cluster_id = config_entry.data[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    # Stelle sicher, dass es nur eine Kalender-Entität gibt
    calendar_entity = DiveraCalendar(coordinator, cluster_id)
    async_add_entities([calendar_entity], update_before_add=True)

    async def async_update_events():
        """Update the calendar with new event data."""
        cluster_data = coordinator.cluster_data
        event_data = cluster_data.get(D_EVENTS, {}).get("items", {})

        if isinstance(event_data, dict):
            calendar_entity.update_events(event_data)
            calendar_entity.async_write_ha_state()

    await async_update_events()
    coordinator.async_add_listener(lambda: asyncio.create_task(async_update_events()))


class DiveraCalendar(CalendarEntity):
    """A single calendar entity for all Divera events."""

    def __init__(self, coordinator, cluster_id) -> None:
        """Initialize the calendar entity."""
        self.coordinator = coordinator
        self.cluster_id = cluster_id
        self._name = coordinator.cluster_name
        self._event_list = []
        self.entity_id = f"calendar.{self.cluster_id}_calendar"
        self.unique_id = f"{self.cluster_id}_calendar"

    @property
    def name(self):
        return self._name

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self._event_list:
            return None

        sorted_events = sorted(
            self._event_list, key=lambda e: parse_datetime(e["start"]["dateTime"])
        )
        return CalendarEvent(
            start=parse_datetime(sorted_events[0]["start"]["dateTime"]),
            end=parse_datetime(sorted_events[0]["end"]["dateTime"]),
            summary=sorted_events[0]["summary"],
            description=sorted_events[0]["description"],
            location=sorted_events[0].get("location"),
        )

    def update_events(self, new_events: dict[str, Any]):
        """Update the event list with new data."""
        self._event_list = []
        for event_id, event_data in new_events.items():
            start = datetime.utcfromtimestamp(event_data.get("start")).replace(
                tzinfo=timezone.utc
            )
            end = datetime.utcfromtimestamp(event_data.get("end")).replace(
                tzinfo=timezone.utc
            )
            self._event_list.append(
                {
                    "start": {"dateTime": start.isoformat()},
                    "end": {"dateTime": end.isoformat()},
                    "summary": event_data.get("title", ""),
                    "description": event_data.get("text", ""),
                    "location": event_data.get("address", ""),
                    "all_day": event_data.get("fullday", False),
                }
            )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ):
        """Return a list of events within the given time range."""
        _LOGGER.debug(f"Fetching events from {start_date} to {end_date}")
        events = []
        for event in self._event_list:
            event_start = parse_datetime(event["start"]["dateTime"])
            event_end = parse_datetime(event["end"]["dateTime"])

            if (
                event_start
                and event_end
                and event_start < end_date
                and event_end > start_date
            ):
                events.append(
                    CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=event["summary"],
                        description=event["description"],
                        location=event["location"],
                    )
                )
        return events
