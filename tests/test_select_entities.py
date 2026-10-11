"""Tests for DiveraControl select entity naming."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.const import (
    D_CLUSTER,
    D_STATUS,
    D_VEHICLE,
)
from custom_components.diveracontrol.select_entity import (
    DiveraUserStatusSelect,
    DiveraVehicleStatusSelect,
)


def _mock_coordinator(hass: HomeAssistant, data: dict) -> MagicMock:
    """Create a lightweight coordinator mock for entity tests."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.cluster_id = "test_cluster_id"
    coordinator.user_name = "Test User"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


def test_user_status_select_is_nameless_main_entity(hass: HomeAssistant) -> None:
    """Test that the user status select has no own name (device name only).

    Entities without their own name are rendered as main entities above the
    frontend divider on the device page, separating the user status from the
    vehicle status selects below.
    """
    coordinator = _mock_coordinator(
        hass,
        {D_CLUSTER: {D_STATUS: {"1": {"name": "Verfügbar"}}}},
    )
    select = DiveraUserStatusSelect(coordinator)

    assert select.has_entity_name is True
    assert select.translation_key is None

    from homeassistant.helpers.entity import UNDEFINED

    assert select.name is UNDEFINED


def test_vehicle_status_select_has_own_name(hass: HomeAssistant) -> None:
    """Test that vehicle status selects carry their own name below the divider."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "v1": {"shortname": "LF", "name": "16-1", "fmsstatus_id": 2}
                }
            }
        },
    )
    select = DiveraVehicleStatusSelect(coordinator, "v1")

    assert select.has_entity_name is False
    assert select.name == "LF / 16-1"


def test_vehicle_status_select_state_options_and_attributes(
    hass: HomeAssistant,
) -> None:
    """Test vehicle select current option, options and extra attributes."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "v1": {"shortname": "LF", "name": "16-1", "fmsstatus_id": 2}
                },
                "fms_status": {
                    "items": {
                        "2": {"number": 2, "name": "Einsatzbereit über Funk"},
                    }
                },
            }
        },
    )
    select = DiveraVehicleStatusSelect(coordinator, "v1")
    assert select.available is True
    assert select.options == ["2 - Einsatzbereit über Funk"]
    assert select.current_option == "2 - Einsatzbereit über Funk"
    assert select.extra_state_attributes["vehicle_id"] == "v1"
    assert select.extra_state_attributes["name"] == "16-1"


def test_vehicle_status_select_unknown_vehicle(hass: HomeAssistant) -> None:
    """Test vehicle select availability and fallbacks for unknown vehicles."""
    coordinator = _mock_coordinator(hass, {D_CLUSTER: {D_VEHICLE: {}}})
    select = DiveraVehicleStatusSelect(coordinator, "gone")
    assert select.available is False
    assert select.current_option is None
    assert select.extra_state_attributes == {}
    assert select.name == "Unknown Vehicle"


def test_vehicle_select_manager_adds_and_removes_entities(
    hass: HomeAssistant,
) -> None:
    """Test that the vehicle select manager syncs entities with coordinator data."""
    from custom_components.diveracontrol.select import DiveraVehicleSelectManager

    coordinator = _mock_coordinator(
        hass, {D_CLUSTER: {D_VEHICLE: {"v1": {"shortname": "LF"}}}}
    )
    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    manager = DiveraVehicleSelectManager(coordinator, async_add_entities)
    manager.start()
    assert len(added) == 1
    assert added[0].vehicle_id == "v1"

    # Simulate a new vehicle appearing in the coordinator data
    coordinator.data = {D_CLUSTER: {D_VEHICLE: {"v1": {}, "v2": {}}}}
    manager._handle_coordinator_update()
    assert len(added) == 2
    assert {entity.vehicle_id for entity in added} == {"v1", "v2"}

    # Simulate a vehicle being removed
    coordinator.data = {D_CLUSTER: {D_VEHICLE: {"v2": {}}}}
    manager._handle_coordinator_update()
    assert manager._known_ids == {"v2"}

    manager.stop()
