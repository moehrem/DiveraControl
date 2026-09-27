"""Tests for DiveraControl device tracker entities."""

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.const import (
    D_ALARM,
    D_CLUSTER,
    D_FMS_STATUS,
    D_VEHICLE,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
)
from custom_components.diveracontrol.device_tracker_entity import (
    DiveraAlarmTracker,
    DiveraAlarmTrackerManager,
    DiveraVehicleTracker,
    DiveraVehicleTrackerManager,
)


def _mock_coordinator(hass: HomeAssistant, data: dict) -> MagicMock:
    """Create a lightweight coordinator mock for entity tests."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


def test_alarm_tracker_properties(hass: HomeAssistant) -> None:
    """Test alarm tracker coordinates and icon selection."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_ALARM: {
                "items": {
                    "a1": {
                        "lat": 51.2,
                        "lng": 7.1,
                        "closed": False,
                        "priority": True,
                    }
                }
            }
        },
    )

    entity = DiveraAlarmTracker(coordinator, "a1")

    assert entity.available is True
    assert entity.latitude == 51.2
    assert entity.longitude == 7.1
    assert entity.icon == I_OPEN_ALARM


def test_alarm_tracker_icon_fallbacks(hass: HomeAssistant) -> None:
    """Test alarm tracker icon fallback for closed and missing alarms."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {"a1": {"closed": True, "priority": True}}}},
    )
    closed_entity = DiveraAlarmTracker(coordinator, "a1")
    missing_entity = DiveraAlarmTracker(coordinator, "missing")

    assert closed_entity.icon == I_CLOSED_ALARM
    assert missing_entity.icon == I_OPEN_ALARM_NOPRIO
    assert missing_entity.available is False


def test_vehicle_tracker_properties(hass: HomeAssistant) -> None:
    """Test vehicle tracker naming, icon and extra attributes."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "v1": {
                        "shortname": "LF",
                        "name": "16-1",
                        "lat": 50.0,
                        "lng": 8.0,
                        "fmsstatus_id": 3,
                    }
                },
                D_FMS_STATUS: {"items": {"3": {"color_hex": "#00FF00"}}},
            }
        },
    )

    entity = DiveraVehicleTracker(coordinator, "v1")

    assert entity.available is True
    assert entity.name == "LF / 16-1"
    assert entity.latitude == 50.0
    assert entity.longitude == 8.0
    assert entity.icon == "mdi:numeric-3-box-outline"
    assert entity.extra_state_attributes == {"icon_color": "#00FF00"}


def test_alarm_tracker_manager_adds_and_removes_entities(hass: HomeAssistant) -> None:
    """Test alarm tracker manager adds new and removes archived entities."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {"new_alarm": {"priority": True}}}},
    )
    added_entities: list = []

    def _add_entities(entities, update_before_add=False):
        added_entities.extend(entities)

    manager = DiveraAlarmTrackerManager(coordinator, _add_entities)
    manager._known_alarm_ids = {"old_alarm"}

    mock_registry = MagicMock()
    mock_registry.async_get_entity_id.return_value = "device_tracker.to_remove"

    with patch(
        "custom_components.diveracontrol.device_tracker_entity.er.async_get",
        return_value=mock_registry,
    ):
        manager._handle_coordinator_update()

    assert len(added_entities) == 1
    assert isinstance(added_entities[0], DiveraAlarmTracker)
    mock_registry.async_remove.assert_called_once_with("device_tracker.to_remove")
    assert manager._known_alarm_ids == {"new_alarm"}


def test_vehicle_tracker_manager_start_stop(hass: HomeAssistant) -> None:
    """Test vehicle tracker manager start/stop registers and unregisters listener."""
    coordinator = _mock_coordinator(
        hass,
        {D_CLUSTER: {D_VEHICLE: {"v1": {}}}},
    )
    add_entities = MagicMock()
    unsub = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=unsub)

    manager = DiveraVehicleTrackerManager(coordinator, add_entities)

    manager.start()
    manager.start()
    manager.stop()

    coordinator.async_add_listener.assert_called_once()
    unsub.assert_called_once()
    assert manager._unsub is None
