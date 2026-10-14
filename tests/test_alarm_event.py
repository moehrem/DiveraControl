"""Tests for the alarm lifecycle event bus manager and device triggers."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol.alarm_event import DiveraAlarmEventBusManager
from custom_components.diveracontrol.const import (
    ALARM_EVENT_TYPE,
    ATTR_ALARM_DATA,
    ATTR_ALARM_EVENT_TYPE,
    ATTR_ALARM_ID,
    D_ALARM,
    D_UCR_ID,
    DOMAIN,
)


def _mock_coordinator(hass: HomeAssistant, data: dict) -> MagicMock:
    """Create a lightweight coordinator mock."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.cluster_id = "test_cluster_id"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


async def test_alarm_event_bus_lifecycle(hass: HomeAssistant) -> None:
    """Test that the manager fires opened/updated/closed on the event bus."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {"a1": {"title": "Alarm Title", "closed": False}}}},
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data={D_UCR_ID: "123456"})
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "123456")},
        name="Test Device",
    )

    events = []

    def _capture(event_type, data):
        events.append((event_type, data))

    hass.bus.async_listen(ALARM_EVENT_TYPE, lambda e: _capture(e.event_type, e.data))

    manager = DiveraAlarmEventBusManager(hass, coordinator)
    manager._handle_coordinator_update()

    assert len(events) == 1
    assert events[0][0] == ALARM_EVENT_TYPE
    assert events[0][1][ATTR_ALARM_EVENT_TYPE] == "opened"
    assert events[0][1][ATTR_ALARM_ID] == "a1"
    assert events[0][1][ATTR_ALARM_DATA]["title"] == "Alarm Title"
    assert events[0][1]["device_id"] == device.id

    coordinator.data = {
        D_ALARM: {"items": {"a1": {"title": "Alarm Title Updated", "closed": False}}}
    }
    manager._handle_coordinator_update()
    assert events[-1][1][ATTR_ALARM_EVENT_TYPE] == "updated"

    coordinator.data = {
        D_ALARM: {"items": {"a1": {"title": "Alarm Title Updated", "closed": True}}}
    }
    manager._handle_coordinator_update()
    assert events[-1][1][ATTR_ALARM_EVENT_TYPE] == "closed"


async def test_alarm_event_bus_no_spurious_events(hass: HomeAssistant) -> None:
    """Test that no events fire for alarms already closed on setup."""
    coordinator = _mock_coordinator(
        hass,
        {D_ALARM: {"items": {"a1": {"title": "Old", "closed": True}}}},
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data={D_UCR_ID: "123456"})
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "123456")},
        name="Test Device",
    )

    fired = []
    hass.bus.async_listen(
        ALARM_EVENT_TYPE, lambda e: fired.append(e.data[ATTR_ALARM_EVENT_TYPE])
    )

    manager = DiveraAlarmEventBusManager(hass, coordinator)
    manager._handle_coordinator_update()
    assert fired == []


async def test_alarm_event_bus_skips_without_device(hass: HomeAssistant) -> None:
    """Test that events are skipped when no device exists for the ucr."""
    coordinator = _mock_coordinator(hass, {D_ALARM: {"items": {}}})
    coordinator.ucr_id = "nonexistent"

    fired = []
    hass.bus.async_listen(ALARM_EVENT_TYPE, lambda e: fired.append(e.data))

    manager = DiveraAlarmEventBusManager(hass, coordinator)
    manager._fire_event("opened", "a1", {"title": "X"})
    assert fired == []


async def test_device_trigger_list_includes_lifecycle_triggers(
    hass: HomeAssistant,
) -> None:
    """Test that async_get_triggers returns the lifecycle triggers."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.diveracontrol.const import (
        TRIGGER_ALARM_CLOSED,
        TRIGGER_ALARM_OPENED,
        TRIGGER_ALARM_UPDATED,
    )
    from custom_components.diveracontrol.device_trigger import async_get_triggers

    config_entry = MockConfigEntry(domain=DOMAIN, data={D_UCR_ID: "123456"})
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "123456")},
        name="Test Device",
    )
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "123456_open_alarms",
        config_entry=config_entry,
        device_id=device.id,
    )

    triggers = await async_get_triggers(hass, device.id)
    types = {t["type"] for t in triggers}
    assert types == {
        "new_alarm",
        "all_alarms_closed",
        TRIGGER_ALARM_OPENED,
        TRIGGER_ALARM_UPDATED,
        TRIGGER_ALARM_CLOSED,
    }
