from datetime import datetime, timedelta, timezone
from homeassistant.util.dt import as_local, parse_datetime
import asyncio
import logging
from homeassistant.core import HomeAssistant
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.entity import generate_entity_id

from .const import DOMAIN, D_CLUSTER_ID, D_COORDINATOR, D_CLUSTER, D_EVENTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up the Divera-Calendar entity."""

    cluster = config_entry.data
    cluster_id = cluster[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    async def sync_events():
        """Synchronize all events with the current data from coordinator."""

        cluster_data = coordinator.cluster_data
        current_events = hass.data[DOMAIN][cluster_id].setdefault("events", {})
        new_events = []

        event_data = cluster_data.get(D_EVENTS, {}).get("items", {})

        if isinstance(event_data, dict):
            event_ids = set(event_data.keys())
        else:
            event_ids = set()

        # Aktualisierung bestehender Events
        for event_id in current_events.keys():
            if event_id in event_ids:
                new_event_data = event_data[event_id]
                old_event = current_events[event_id]

                # Prüfe, ob sich etwas geändert hat
                if (
                    old_event.event_data["title"] != new_event_data["title"]
                    or old_event.event_data["start"] != new_event_data["start"]
                    or old_event.event_data["end"] != new_event_data["end"]
                    or old_event.event_data.get("text", "")
                    != new_event_data.get("text", "")
                ):
                    _LOGGER.info(
                        f"Aktualisiere Event {event_id}: {new_event_data['title']}"
                    )

                    # Aktualisiere die Daten des bestehenden Events
                    old_event.event_data = new_event_data
                    await old_event.async_update()

        # Neue Events hinzufügen
        for event_id in event_ids - current_events.keys():
            event_data_entry = event_data[event_id]
            calendar_entity = DiveraCalendar(
                coordinator, cluster_data, event_data_entry, cluster_id
            )
            current_events[event_id] = calendar_entity
            new_events.append(calendar_entity)

        # Neue Kalender-Entitäten registrieren
        if new_events:
            async_add_entities(new_events, update_before_add=True)

    await sync_events()

    # Listener für Updates hinzufügen
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_events()))


class DiveraCalendar(CalendarEntity):
    """A Calendar entity for Divera events."""

    def __init__(self, coordinator, cluster_data, event_data, cluster_id):
        """Initialisiere den Kalender."""
        self.coordinator = coordinator
        self.cluster_data = cluster_data
        self.event_data = event_data
        self.cluster_id = cluster_id

        self._name = f"Divera Kalender {event_data['title']}"
        self._event_list = []
        self.entity_id = f"calendar.divera_{self.cluster_id}_{event_data['title'].replace(' ', '_').lower()}"

    @property
    def name(self):
        """Gibt den Namen des Kalenders zurück."""
        return self._name

    @property
    def event(self) -> CalendarEvent | None:
        """Gibt das nächste bevorstehende Event zurück."""
        if not self._event_list:
            return None

        event_data = self._event_list[0]

        return CalendarEvent(
            summary=event_data["summary"],
            description=event_data["description"],
            start=parse_datetime(event_data["start"]["dateTime"]),
            end=parse_datetime(event_data["end"]["dateTime"]),
        )

    async def async_update(self):
        """Neue Events von der Divera API abrufen."""
        _LOGGER.debug(f"Updating event: {self.event_data['title']}")

        # Daten direkt aus `self.event_data` verwenden (aktualisierte Daten)
        start = datetime.utcfromtimestamp(self.event_data["start"]).replace(
            tzinfo=timezone.utc
        )
        end = datetime.utcfromtimestamp(self.event_data["end"]).replace(
            tzinfo=timezone.utc
        )

        self._event_list = [
            {
                "summary": self.event_data["title"],
                "description": self.event_data.get("text", ""),
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
            }
        ]

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime):
        """Rückgabe einer Liste von Events innerhalb des angegebenen Zeitraums."""
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
                        summary=event["summary"],
                        description=event["description"],
                        start=event_start,
                        end=event_end,
                    )
                )

        return events
