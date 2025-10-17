"""Tests for DiveraControl calendar platform."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from custom_components.diveracontrol.calendar_entity import DiveraCalendar
from custom_components.diveracontrol.const import D_EVENTS


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.cluster_name = "Test Cluster"
    coordinator.data = {
        D_EVENTS: {
            "items": {
                "1": {
                    "title": "Test Event 1",
                    "text": "Test Description 1",
                    "address": "Test Location 1",
                    "start": 1638360000,  # 2021-12-01 12:00:00 UTC
                    "end": 1638363600,  # 2021-12-01 13:00:00 UTC
                    "fullday": False,
                },
                "2": {
                    "title": "Test Event 2",
                    "text": "Test Description 2",
                    "address": "Test Location 2",
                    "start": 1638446400,  # 2021-12-02 12:00:00 UTC
                    "end": 1638450000,  # 2021-12-02 13:00:00 UTC
                    "fullday": False,
                },
            }
        }
    }
    return coordinator


@pytest.fixture
def calendar_entity(mock_coordinator):
    """Create a calendar entity."""
    entity = DiveraCalendar(mock_coordinator, "test_ucr")
    return entity


class TestDiveraCalendar:
    """Test DiveraCalendar entity."""

    def test_init(self, calendar_entity, mock_coordinator):
        """Test calendar entity initialization."""
        assert calendar_entity.ucr_id == "test_ucr"
        assert calendar_entity._attr_unique_id == "test_ucr_calendar"
        assert calendar_entity.entity_id == "calendar.test_ucr_calendar"
        assert calendar_entity._attr_has_entity_name is True
        assert calendar_entity._attr_name is None
        assert calendar_entity._attr_entity_category.name == "DIAGNOSTIC"
        assert calendar_entity._event_list == []

    def test_handle_coordinator_update(self, calendar_entity, mock_coordinator):
        """Test coordinator update handling."""
        # Mock async_write_ha_state to avoid hass requirement
        calendar_entity.async_write_ha_state = MagicMock()

        calendar_entity._handle_coordinator_update()

        assert len(calendar_entity._event_list) == 2
        assert calendar_entity._event_list[0]["summary"] == "Test Event 1"
        assert calendar_entity._event_list[1]["summary"] == "Test Event 2"

        # Verify async_write_ha_state was called
        calendar_entity.async_write_ha_state.assert_called_once()

    def test_event_property_no_events(self, calendar_entity):
        """Test event property when no events exist."""
        assert calendar_entity.event is None

    def test_event_property_with_future_events(self, calendar_entity):
        """Test event property with future events."""
        # Set up events in the past and future
        past_time = datetime.now(UTC) - timedelta(hours=2)
        future_time = datetime.now(UTC) + timedelta(hours=2)

        calendar_entity._event_list = [
            {
                "start": {"dateTime": past_time.isoformat()},
                "end": {"dateTime": (past_time + timedelta(hours=1)).isoformat()},
                "summary": "Past Event",
                "description": "Past Description",
                "location": "Past Location",
            },
            {
                "start": {"dateTime": future_time.isoformat()},
                "end": {"dateTime": (future_time + timedelta(hours=1)).isoformat()},
                "summary": "Future Event",
                "description": "Future Description",
                "location": "Future Location",
            },
        ]

        event = calendar_entity.event
        assert event is not None
        assert event.summary == "Future Event"
        assert event.description == "Future Description"
        assert event.location == "Future Location"

    def test_event_property_only_past_events(self, calendar_entity):
        """Test event property when only past events exist."""
        past_time = datetime.now(UTC) - timedelta(hours=2)

        calendar_entity._event_list = [
            {
                "start": {"dateTime": past_time.isoformat()},
                "end": {"dateTime": (past_time + timedelta(hours=1)).isoformat()},
                "summary": "Past Event",
            }
        ]

        assert calendar_entity.event is None

    def test_event_property_invalid_datetime(self, calendar_entity):
        """Test event property with invalid datetime."""
        future_time = datetime.now(UTC) + timedelta(hours=2)

        calendar_entity._event_list = [
            {
                "start": {"dateTime": future_time.isoformat()},
                "end": {"dateTime": "invalid-datetime"},
                "summary": "Invalid Event",
            }
        ]

        assert calendar_entity.event is None

    def test_update_events_valid_data(self, calendar_entity):
        """Test update_events with valid data."""
        event_items = {
            "1": {
                "title": "Event 1",
                "text": "Description 1",
                "address": "Location 1",
                "start": 1638360000,
                "end": 1638363600,
                "fullday": False,
            }
        }

        calendar_entity.update_events(event_items)

        assert len(calendar_entity._event_list) == 1
        event = calendar_entity._event_list[0]
        assert event["summary"] == "Event 1"
        assert event["description"] == "Description 1"
        assert event["location"] == "Location 1"
        assert event["all_day"] is False
        assert "dateTime" in event["start"]
        assert "dateTime" in event["end"]

    def test_update_events_invalid_timestamps(self, calendar_entity):
        """Test update_events with invalid timestamps."""
        event_items = {
            "1": {
                "title": "Event 1",
                "start": 0,  # Invalid start
                "end": 1638363600,
            },
            "2": {
                "title": "Event 2",
                "start": 1638360000,
                "end": 0,  # Invalid end
            },
            "3": {
                "title": "Event 3",
                "start": 1638360000,
                "end": 1638363600,
            },
        }

        calendar_entity.update_events(event_items)

        # Only event 3 should be included (valid timestamps)
        assert len(calendar_entity._event_list) == 1
        assert calendar_entity._event_list[0]["summary"] == "Event 3"

    def test_update_events_missing_fields(self, calendar_entity):
        """Test update_events with missing fields."""
        event_items = {
            "1": {
                # Missing title, text, address
                "start": 1638360000,
                "end": 1638363600,
            }
        }

        calendar_entity.update_events(event_items)

        assert len(calendar_entity._event_list) == 1
        event = calendar_entity._event_list[0]
        assert event["summary"] == "Kein Titel"  # Default title
        assert event["description"] == ""  # Default description
        assert event["location"] == ""  # Default location

    def test_update_events_empty_data(self, calendar_entity):
        """Test update_events with empty data."""
        calendar_entity.update_events({})
        assert calendar_entity._event_list == []

    async def test_async_get_events_no_events(self, calendar_entity, hass):
        """Test async_get_events with no events."""
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=1)

        events = await calendar_entity.async_get_events(hass, start_date, end_date)
        assert events == []

    async def test_async_get_events_with_events(self, calendar_entity, hass):
        """Test async_get_events with events in range."""
        now = datetime.now(UTC)
        calendar_entity._event_list = [
            {
                "start": {"dateTime": (now + timedelta(hours=1)).isoformat()},
                "end": {"dateTime": (now + timedelta(hours=2)).isoformat()},
                "summary": "Event in range",
                "description": "Description",
                "location": "Location",
            },
            {
                "start": {"dateTime": (now + timedelta(days=2)).isoformat()},
                "end": {"dateTime": (now + timedelta(days=2, hours=1)).isoformat()},
                "summary": "Event out of range",
            },
        ]

        start_date = now
        end_date = now + timedelta(days=1)

        events = await calendar_entity.async_get_events(hass, start_date, end_date)

        assert len(events) == 1
        assert events[0].summary == "Event in range"

    async def test_async_get_events_invalid_datetime(self, calendar_entity, hass):
        """Test async_get_events with invalid datetime strings."""
        now = datetime.now(UTC)
        calendar_entity._event_list = [
            {
                "start": {"dateTime": (now + timedelta(hours=1)).isoformat()},
                "end": {"dateTime": "invalid-datetime"},
                "summary": "Invalid event",
            }
        ]

        start_date = now
        end_date = now + timedelta(days=1)

        events = await calendar_entity.async_get_events(hass, start_date, end_date)
        assert events == []

    async def test_async_get_events_overlapping_range(self, calendar_entity, hass):
        """Test async_get_events with events overlapping the range."""
        now = datetime.now(UTC)
        calendar_entity._event_list = [
            {
                "start": {"dateTime": (now - timedelta(hours=1)).isoformat()},
                "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
                "summary": "Event overlapping start",
            },
            {
                "start": {"dateTime": (now + timedelta(hours=23)).isoformat()},
                "end": {"dateTime": (now + timedelta(hours=25)).isoformat()},
                "summary": "Event overlapping end",
            },
        ]

        start_date = now
        end_date = now + timedelta(days=1)

        events = await calendar_entity.async_get_events(hass, start_date, end_date)

        assert len(events) == 2
        assert events[0].summary == "Event overlapping start"
        assert events[1].summary == "Event overlapping end"
