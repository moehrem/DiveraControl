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
