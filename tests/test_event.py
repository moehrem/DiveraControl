"""Tests for DiveraControl event entities."""

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.const import (
    D_ALARM,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
)
from custom_components.diveracontrol.event import DiveraAlarmEventManager
from custom_components.diveracontrol.event_entity import DiveraAlarmEvent


def _mock_coordinator(hass: HomeAssistant, data: dict) -> MagicMock:
    """Create a lightweight coordinator mock for entity tests."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.cluster_id = "test_cluster_id"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


def test_alarm_event_name_attributes_icon(hass: HomeAssistant) -> None:
    """Test alarm event name, attributes and icon behavior."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_ALARM: {
                "items": {
                    "a1": {"title": "Alarm Title", "closed": True},
                    "a2": {"title": "Prio Alarm", "closed": False, "priority": True},
                }
            }
        },
    )
    alarm = DiveraAlarmEvent(coordinator, "a1")
    prio_alarm = DiveraAlarmEvent(coordinator, "a2")
    missing_alarm = DiveraAlarmEvent(coordinator, "unknown")

    assert alarm.entity_id == "event.123456_alarm_a1"
    assert alarm.name == "Alarm Title"
    assert alarm.translation_key == "alarm"
    assert alarm.event_types == ["triggered", "updated", "closed"]
    assert alarm.extra_state_attributes["alarm_id"] == "a1"
    assert alarm.extra_state_attributes["title"] == "Alarm Title"
    assert alarm.icon == I_CLOSED_ALARM
    assert prio_alarm.icon == I_OPEN_ALARM
    assert missing_alarm.available is False
    assert missing_alarm.icon == I_OPEN_ALARM_NOPRIO


def test_alarm_event_manager_keeps_closed_alarms(hass: HomeAssistant) -> None:
    """Test that closed alarms stay until Divera archives them."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_ALARM: {
                "items": {
                    "open_alarm": {"title": "N", "closed": False},
                    "closed_alarm": {"title": "C", "closed": True},
                }
            }
        },
    )
    added_entities: list = []

    def _add_entities(entities, update_before_add=False):
        added_entities.extend(entities)

    manager = DiveraAlarmEventManager(coordinator, _add_entities)
    manager._handle_coordinator_update()

    assert len(added_entities) == 2
    assert all(isinstance(entity, DiveraAlarmEvent) for entity in added_entities)
    assert manager._known_ids == {"open_alarm", "closed_alarm"}

    # Closing the open alarm must NOT remove its entity
    manager._handle_coordinator_update()
    assert manager._known_ids == {"open_alarm", "closed_alarm"}


def test_alarm_event_manager_removes_archived_alarms(hass: HomeAssistant) -> None:
    """Test that entities are removed once Divera archives the alarm."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {}}},
    )
    added_entities: list = []

    def _add_entities(entities, update_before_add=False):
        added_entities.extend(entities)

    manager = DiveraAlarmEventManager(coordinator, _add_entities)
    manager._known_ids = {"archived_alarm"}

    mock_registry = MagicMock()
    mock_registry.async_get_entity_id.return_value = "event.to_remove"
    with patch(
        "custom_components.diveracontrol.event.er.async_get",
        return_value=mock_registry,
    ):
        manager._handle_coordinator_update()

    mock_registry.async_remove.assert_called_once_with("event.to_remove")
    assert manager._known_ids == set()


def test_alarm_event_manager_removes_closed_alarms(hass: HomeAssistant) -> None:
    """Test that the manager removes entities for alarms that closed."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {}}},
    )
    added_entities: list = []

    def _add_entities(entities, update_before_add=False):
        added_entities.extend(entities)

    manager = DiveraAlarmEventManager(coordinator, _add_entities)
    manager._known_ids = {"gone_alarm"}

    mock_registry = MagicMock()
    mock_registry.async_get_entity_id.return_value = "event.to_remove"
    with patch(
        "custom_components.diveracontrol.event.er.async_get",
        return_value=mock_registry,
    ):
        manager._handle_coordinator_update()

    mock_registry.async_remove.assert_called_once_with("event.to_remove")
    assert manager._known_ids == set()


async def test_alarm_event_fires_triggered_on_add(hass: HomeAssistant) -> None:
    """Test that a newly created alarm event fires triggered immediately."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {"a1": {"title": "Alarm Title", "closed": False}}}},
    )
    alarm = DiveraAlarmEvent(coordinator, "a1")

    with patch.object(DiveraAlarmEvent, "async_get_last_state", return_value=None):
        await alarm.async_added_to_hass()

    assert alarm.state is not None
    assert alarm.state_attributes["event_type"] == "triggered"
    assert alarm.state_attributes["title"] == "Alarm Title"


async def test_alarm_event_does_not_refire_triggered_after_restart(
    hass: HomeAssistant,
) -> None:
    """Test that a restored alarm event does not fire triggered again."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {"a1": {"title": "Alarm Title", "closed": False}}}},
    )
    alarm = DiveraAlarmEvent(coordinator, "a1")

    with patch.object(
        DiveraAlarmEvent, "async_get_last_state", return_value=MagicMock()
    ):
        await alarm.async_added_to_hass()

    assert alarm.state is None
    assert alarm._fired_initial_event is True
