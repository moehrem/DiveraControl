"""Tests for DiveraControl calendar entities."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.const import D_EVENTS
from custom_components.diveracontrol.calendar_entity import DiveraCalendar


def _create_coordinator(hass: HomeAssistant, data: dict | None = None) -> MagicMock:
    """Create a coordinator mock for entity tests."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data or {}
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.cluster_id = "test_cluster_id"
    coordinator.user_name = "Test User"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


class TestDiveraCalendar:
    """Test DiveraCalendar entity."""

    def test_init(self, hass: HomeAssistant) -> None:
        """Test calendar entity initialization."""
        coordinator = _create_coordinator(hass)
        entity = DiveraCalendar(coordinator)
        
        assert entity.ucr_id == "123456"
        assert entity.unique_id == "123456_calendar"
        assert entity.entity_id == "calendar.123456_calendar"
        assert entity._event_list == []

    def test_event_property_no_events(self, hass: HomeAssistant) -> None:
        """Test event property when no events exist."""
        coordinator = _create_coordinator(hass)
        entity = DiveraCalendar(coordinator)
        assert entity.event is None

    def test_update_events_valid_data(self, hass: HomeAssistant) -> None:
        """Test update_events with valid data."""
        coordinator = _create_coordinator(hass)
        entity = DiveraCalendar(coordinator)

        event_items = {
            "event1": {
                "start": 1700000000,
                "end": 1700003600,
                "title": "Test Event",
                "text": "Description",
                "address": "Location",
                "fullday": False,
            }
        }

        entity.update_events(event_items)
        assert len(entity._event_list) == 1
        assert entity._event_list[0]["summary"] == "Test Event"

    def test_update_events_invalid_timestamps(self, hass: HomeAssistant) -> None:
        """Test update_events with invalid timestamps."""
        coordinator = _create_coordinator(hass)
        entity = DiveraCalendar(coordinator)

        event_items = {
            "event1": {
                "start": 0,
                "end": 0,
                "title": "Invalid Event",
                "text": "",
                "address": "",
                "fullday": False,
            }
        }

        entity.update_events(event_items)
        assert len(entity._event_list) == 0

    def test_update_events_missing_fields(self, hass: HomeAssistant) -> None:
        """Test update_events with missing required fields."""
        coordinator = _create_coordinator(hass)
        entity = DiveraCalendar(coordinator)

        event_items = {
            "event1": {
                "title": "Incomplete Event",
            }
        }

        entity.update_events(event_items)
        assert len(entity._event_list) == 0

    def test_update_events_empty_data(self, hass: HomeAssistant) -> None:
        """Test update_events with empty data."""
        coordinator = _create_coordinator(hass)
        entity = DiveraCalendar(coordinator)

        entity.update_events({})
        assert len(entity._event_list) == 0
