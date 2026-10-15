"""Tests for DiveraControl select entity naming."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.divera_permissions import DiveraPermissions

from custom_components.diveracontrol.const import (
    D_CLUSTER,
    D_STATUS,
    D_VEHICLE,
)
from custom_components.diveracontrol.select_entity import (
    DiveraUserStatusSelect,
    DiveraVehicleStatusSelect,
)


def _mock_coordinator(
    hass: HomeAssistant,
    data: dict,
    permissions: DiveraPermissions | None = None,
) -> MagicMock:
    """Create a lightweight coordinator mock for entity tests.

    By default a management permission set is attached so write access is
    granted; tests for permission gating pass a restricted instance.
    """
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.cluster_id = "test_cluster_id"
    coordinator.user_name = "Test User"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    if permissions is None:
        permissions = DiveraPermissions()
        permissions.ucr_id = "123456"
        permissions.replace_permissions_from_ucr_data(
            {"data": {"user": {"access": {"management": True}}}}
        )
    coordinator.api.permissions = permissions
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


def _permissions(access: dict) -> DiveraPermissions:
    """Create a DiveraPermissions instance from a raw access block."""
    permissions = DiveraPermissions()
    permissions.ucr_id = "123456"
    permissions.replace_permissions_from_ucr_data(
        {"data": {"user": {"access": access}}}
    )
    return permissions


def test_vehicle_select_manager_gates_on_permissions(hass: HomeAssistant) -> None:
    """Test that the vehicle select manager only creates writable selects."""
    from custom_components.diveracontrol.select import DiveraVehicleSelectManager

    vehicle_data = {D_CLUSTER: {D_VEHICLE: {"v1": {}, "v2": {}}}}

    # full write access: all vehicles become selects
    coordinator = _mock_coordinator(
        hass,
        dict(vehicle_data),
        permissions=_permissions(
            {
                "status": True,
                "status_vehicle": True,
                "status_actions": {"vehicle_all": True, "vehicle_ids": []},
            }
        ),
    )
    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    manager = DiveraVehicleSelectManager(coordinator, async_add_entities)
    manager.start()
    assert {entity.vehicle_id for entity in added} == {"v1", "v2"}
    manager.stop()

    # restricted to v1: only v1 becomes a select
    coordinator = _mock_coordinator(
        hass,
        dict(vehicle_data),
        permissions=_permissions(
            {
                "status": True,
                "status_vehicle": True,
                "status_actions": {"vehicle_all": False, "vehicle_ids": ["v1"]},
            }
        ),
    )
    added.clear()
    manager = DiveraVehicleSelectManager(coordinator, async_add_entities)
    manager.start()
    assert {entity.vehicle_id for entity in added} == {"v1"}
    manager.stop()

    # no vehicle write permission at all: no selects are created
    coordinator = _mock_coordinator(
        hass,
        dict(vehicle_data),
        permissions=_permissions(
            {
                "status": True,
                "status_vehicle": False,
                "status_actions": {"vehicle_all": False, "vehicle_ids": []},
            }
        ),
    )
    added.clear()
    manager = DiveraVehicleSelectManager(coordinator, async_add_entities)
    manager.start()
    assert added == []
    manager.stop()


def test_vehicle_status_sensor_manager_creates_readonly_sensors(
    hass: HomeAssistant,
) -> None:
    """Test that vehicles without write access get a read-only sensor."""
    from custom_components.diveracontrol.sensor_entity import (
        DiveraVehicleStatusSensorManager,
    )

    vehicle_data = {
        D_CLUSTER: {
            D_VEHICLE: {
                "v1": {
                    "shortname": "LF",
                    "name": "16-1",
                    "fmsstatus_id": 2,
                },
                "v2": {"shortname": "MZF", "name": "14-1", "fmsstatus_id": 3},
            },
            "fms_status": {
                "items": {
                    "2": {"number": 2, "name": "Einsatzbereit über Funk"},
                    "3": {"number": 3, "name": "Auf Anfahrt"},
                }
            },
        }
    }

    coordinator = _mock_coordinator(
        hass,
        vehicle_data,
        permissions=_permissions(
            {
                "status": True,
                "status_vehicle": False,
                "status_actions": {"vehicle_all": False, "vehicle_ids": []},
            }
        ),
    )
    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    manager = DiveraVehicleStatusSensorManager(coordinator, async_add_entities)
    manager.start()
    assert {entity.vehicle_id for entity in added} == {"v1", "v2"}
    sensor = next(entity for entity in added if entity.vehicle_id == "v1")
    assert sensor.state == "2 - Einsatzbereit über Funk"
    assert sensor.extra_state_attributes["vehicle_id"] == "v1"
    manager.stop()


def test_user_status_sensor_created_without_write_permission(
    hass: HomeAssistant,
) -> None:
    """Test the read-only user status sensor."""
    from custom_components.diveracontrol.sensor_entity import (
        DiveraUserStatusSensor,
        DiveraUserStatusSensorManager,
    )

    data = {
        D_CLUSTER: {D_STATUS: {"1": {"name": "Verfügbar"}, "2": {"name": "5 Minuten"}}},
        "status": {"status_id": 2, "note": "", "vehicle": 0},
    }
    coordinator = _mock_coordinator(
        hass,
        data,
        permissions=_permissions(
            {
                "status": True,
                "status_manual": False,
                "status_actions": {"set_all": False, "set_ids": []},
            }
        ),
    )
    sensor = DiveraUserStatusSensor(coordinator, "user_status")
    assert sensor.state == "5 Minuten"
    assert sensor.extra_state_attributes["status_id"] == 2

    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    manager = DiveraUserStatusSensorManager(coordinator, async_add_entities)
    manager.start()
    assert len(added) == 1
    manager.stop()

    # with write permission no read-only sensor is created
    coordinator = _mock_coordinator(
        hass,
        data,
        permissions=_permissions(
            {
                "status": True,
                "status_manual": True,
                "status_actions": {"set_all": True, "set_ids": []},
            }
        ),
    )
    added.clear()
    manager = DiveraUserStatusSensorManager(coordinator, async_add_entities)
    manager.start()
    assert added == []
    manager.stop()


def test_availability_sensor_manager_gates_on_status_permission(
    hass: HomeAssistant,
) -> None:
    """Test that availability sensors are only created with status access."""
    from custom_components.diveracontrol.sensor_entity import (
        DiveraAvailabilitySensorManager,
    )

    data = {D_CLUSTER: {D_STATUS: {"1": {"name": "Verfügbar"}}}}

    # status permission granted: sensor is created
    coordinator = _mock_coordinator(
        hass,
        dict(data),
        permissions=_permissions({"status": True}),
    )
    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    manager = DiveraAvailabilitySensorManager(coordinator, async_add_entities)
    manager.start()
    assert len(added) == 1
    manager.stop()

    # status permission denied: no sensor is created
    coordinator = _mock_coordinator(
        hass,
        dict(data),
        permissions=_permissions({"status": False}),
    )
    added.clear()
    manager = DiveraAvailabilitySensorManager(coordinator, async_add_entities)
    manager.start()
    assert added == []
    manager.stop()


def test_user_status_select_manager_is_dynamic(hass: HomeAssistant) -> None:
    """Test that the user status select reacts to permission changes."""
    from custom_components.diveracontrol.select import (
        DiveraUserStatusSelectManager,
    )

    data = {D_CLUSTER: {D_STATUS: {"1": {"name": "Verfügbar"}}}}

    # with write permission the select is created
    coordinator = _mock_coordinator(
        hass,
        dict(data),
        permissions=_permissions(
            {
                "status": True,
                "status_manual": True,
                "status_actions": {"set_all": True, "set_ids": []},
            }
        ),
    )
    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    manager = DiveraUserStatusSelectManager(coordinator, async_add_entities)
    manager.start()
    assert len(added) == 1
    assert manager._known_ids == {"user_status"}

    # permission revoked at runtime: the select is removed again
    coordinator.api.permissions = _permissions(
        {
            "status": False,
            "status_manual": False,
            "status_actions": {"set_all": True, "set_ids": []},
        }
    )
    manager._handle_coordinator_update()
    assert manager._known_ids == set()

    # permission re-granted: the select comes back
    coordinator.api.permissions = _permissions(
        {
            "status": True,
            "status_manual": True,
            "status_actions": {"set_all": True, "set_ids": []},
        }
    )
    manager._handle_coordinator_update()
    assert manager._known_ids == {"user_status"}
    assert len(added) == 2
    manager.stop()


def test_no_permission_dataset_denies_all_status_writes(hass: HomeAssistant) -> None:
    """Regression test with the Divera dataset of a user without permissions.

    Divera delivers misleading status_actions defaults (set_all/vehicle_all
    true) even when all status access flags are false; none of these may
    grant write access.
    """
    from custom_components.diveracontrol.select import (
        DiveraUserStatusSelectManager,
        DiveraVehicleSelectManager,
    )

    no_permission_access = {
        "messages": False,
        "alarm": False,
        "news": False,
        "status": False,
        "status_manual": False,
        "status_planer": False,
        "status_geofence": False,
        "status_vehicle": False,
        "status_actions": {
            "set_all": True,
            "set_ids": [],
            "vehicle_all": True,
            "vehicle_ids": [],
        },
        "management": False,
    }
    permissions = _permissions(no_permission_access)
    assert not permissions.can_write_user_status()
    assert not permissions.can_write_vehicle_status("222222")
    assert not permissions.has_status_permission()

    data = {
        D_CLUSTER: {
            D_VEHICLE: {
                "222222": {"shortname": "MZF", "name": "11-22-33", "fmsstatus_id": 2}
            },
            D_STATUS: {"333333": {"name": "Status A"}},
        }
    }
    coordinator = _mock_coordinator(hass, data, permissions=permissions)
    added: list = []

    def async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    user_manager = DiveraUserStatusSelectManager(coordinator, async_add_entities)
    user_manager.start()
    vehicle_manager = DiveraVehicleSelectManager(coordinator, async_add_entities)
    vehicle_manager.start()
    assert added == []
    user_manager.stop()
    vehicle_manager.stop()


def test_user_status_select_options_filtered_by_set_ids(hass: HomeAssistant) -> None:
    """Test that the user status select only offers permitted statuses."""
    data = {
        D_CLUSTER: {
            D_STATUS: {
                "1": {"name": "Verfügbar"},
                "2": {"name": "Eingeschränkt A"},
                "3": {"name": "Eingeschränkt B"},
            }
        }
    }

    # set_ids limits the selectable statuses to 1 and 2
    coordinator = _mock_coordinator(
        hass,
        data,
        permissions=_permissions(
            {
                "status": True,
                "status_manual": True,
                "status_actions": {"set_all": False, "set_ids": [1, 2]},
            }
        ),
    )
    select = DiveraUserStatusSelect(coordinator)
    assert select.options == ["Verfügbar", "Eingeschränkt A"]

    # set_all permits every status
    coordinator = _mock_coordinator(
        hass,
        data,
        permissions=_permissions(
            {
                "status": True,
                "status_manual": True,
                "status_actions": {"set_all": True, "set_ids": []},
            }
        ),
    )
    select = DiveraUserStatusSelect(coordinator)
    assert select.options == ["Verfügbar", "Eingeschränkt A", "Eingeschränkt B"]


def test_user_status_select_option_rejected_without_permission(
    hass: HomeAssistant,
) -> None:
    """Test that selecting a non-permitted status raises an error."""
    from homeassistant.exceptions import HomeAssistantError

    data = {
        D_CLUSTER: {D_STATUS: {"1": {"name": "Verfügbar"}, "3": {"name": "Gesperrt"}}}
    }
    coordinator = _mock_coordinator(
        hass,
        data,
        permissions=_permissions(
            {
                "status": True,
                "status_manual": True,
                "status_actions": {"set_all": False, "set_ids": [1]},
            }
        ),
    )
    select = DiveraUserStatusSelect(coordinator)
    assert select.options == ["Verfügbar"]

    import pytest

    with pytest.raises(HomeAssistantError):
        select.hass = hass
        hass.services.async_register(
            "diveracontrol", "post_user_status", lambda call: None
        )
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            select.async_select_option("Gesperrt")
        )
