"""Manage calendar and event creation and updating based on Divera events."""

import asyncio
from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import parse_datetime

from .const import D_CLUSTER_NAME, D_COORDINATOR, D_EVENTS, D_UCR_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Divera-Calendar entity."""
    ucr_id = config_entry.data[D_UCR_ID]
    coordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]

    # ensure only one calendar entity exist at a time
    calendar_entity = DiveraCalendar(coordinator, ucr_id)
    async_add_entities([calendar_entity], update_before_add=False)

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

    def __init__(self, coordinator, ucr_id) -> None:
        """Initialize the calendar entity."""
        self._name = coordinator.admin_data.get(D_CLUSTER_NAME)
        self._event_list = []
        self.entity_id = f"calendar.{ucr_id}_calendar"
        self.unique_id = f"{ucr_id}_calendar"

    @property
    def name(self):
        """Return the name of calendar."""
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
        for event_data in new_events.values():
            start = datetime.fromtimestamp(event_data.get("start")).replace(tzinfo=UTC)
            end = datetime.fromtimestamp(event_data.get("end")).replace(tzinfo=UTC)

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
        _LOGGER.debug("Fetching events from %s to %s", start_date, end_date)
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
