"""Manage calendar and event creation and updating based on Divera events."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import parse_datetime

from .const import D_CLUSTER_NAME, D_COORDINATOR, D_EVENTS, D_UCR_ID, DOMAIN
from .coordinator import DiveraCoordinator
from .utils import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Divera-Calendar entity.

    Args:
        hass (HomeAssistant): HomeAssistant instance.
        config_entry (dict[str, Any]): configuration entry data.
        async_add_entities (Callable): function to add calendar entites.

    Returns:
        None

    """
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

    def __init__(
        self,
        coordinator: DiveraCoordinator,
        ucr_id: str,
    ) -> None:
        """Initialize the calendar entity.

        Args:
            coordinator (DiveraCoordinator): coordinator instance.
            ucr_id (str): user_cluster_relation, ID to identify Divera user.

        Returns:
            None

        """
        self.cluster_name = coordinator.admin_data[D_CLUSTER_NAME]

        self._attr_device_info = get_device_info(self.cluster_name)
        self._attr_name = coordinator.admin_data.get(D_CLUSTER_NAME)
        self._event_list: list[dict[str, Any]] = []
        self.entity_id = f"calendar.{ucr_id}_calendar"
        self._attr_unique_id = f"{ucr_id}_calendar"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self._event_list:
            return None

        sorted_events = sorted(
            self._event_list,
            key=lambda e: parse_datetime(e["start"]["dateTime"]) or datetime.min,
        )
        first_event = sorted_events[0]

        return CalendarEvent(
            start=parse_datetime(first_event["start"]["dateTime"]) or datetime.min,
            end=parse_datetime(first_event["end"]["dateTime"]) or datetime.min,
            summary=first_event["summary"],
            description=first_event["description"],
            location=first_event.get("location"),
        )

    def update_events(
        self,
        new_events: dict[str, Any],
    ) -> None:
        """Update the event list with new data.

        Args:
            new_events (dict[str, Any]): Dictionary containing event data.

        Returns:
            None

        """
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
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return a list of events within the given time range.

        Args:
            hass (HomeAssistant): HomeAssistant instance.
            start_date (datetime): Start date of the range.
            end_date (datetime): End date of the range.

        Returns:
            list[CalendarEvent]: List of calendar events within the range.

        """

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
