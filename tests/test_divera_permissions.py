"""Tests for DiveraPermissions granular status write access."""

from homeassistant.exceptions import HomeAssistantError

from custom_components.diveracontrol.divera_permissions import DiveraPermissions


def _permissions(access: dict, ucr_id: str = "641834") -> DiveraPermissions:
    """Create a DiveraPermissions instance from a raw access block."""
    permissions = DiveraPermissions()
    permissions.ucr_id = ucr_id
    permissions.replace_permissions_from_ucr_data(
        {"data": {"user": {"access": access}}}
    )
    return permissions


FULL_ACCESS = {
    "status": True,
    "status_vehicle": True,
    "status_manual": True,
    "status_actions": {
        "set_all": True,
        "set_ids": [],
        "vehicle_all": True,
        "vehicle_ids": [],
    },
}


def test_full_access_grants_all_writes() -> None:
    """Full status access (as in the Divera test dataset) grants everything."""
    permissions = _permissions(FULL_ACCESS)
    assert permissions.can_write_vehicle_status("113090")
    assert permissions.can_write_user_status()
    assert permissions.has_status_permission()


def test_vehicle_ids_restricts_vehicle_writes() -> None:
    """vehicle_all=False limits writes to the vehicles in vehicle_ids."""
    permissions = _permissions(
        {
            **FULL_ACCESS,
            "status_actions": {
                "set_all": True,
                "set_ids": [],
                "vehicle_all": False,
                "vehicle_ids": [113090],
            },
        }
    )
    assert permissions.can_write_vehicle_status("113090")
    assert permissions.can_write_vehicle_status(113090)
    assert not permissions.can_write_vehicle_status("113091")


def test_status_vehicle_false_denies_all_vehicle_writes() -> None:
    """Without status_vehicle no vehicle may be written, even via ids."""
    permissions = _permissions(
        {
            **FULL_ACCESS,
            "status_vehicle": False,
            "status_actions": {
                **FULL_ACCESS["status_actions"],
                "vehicle_all": False,
                "vehicle_ids": [113090],
            },
        }
    )
    assert not permissions.can_write_vehicle_status("113090")
    assert not permissions.can_write_vehicle_status(None)


def test_set_ids_restricts_user_status_writes() -> None:
    """set_all=False limits user status writes to the relations in set_ids."""
    permissions = _permissions(
        {
            **FULL_ACCESS,
            "status_actions": {
                "set_all": False,
                "set_ids": ["641834"],
                "vehicle_all": True,
                "vehicle_ids": [],
            },
        }
    )
    assert permissions.can_write_user_status()

    permissions = _permissions(
        {
            **FULL_ACCESS,
            "status_actions": {
                "set_all": False,
                "set_ids": ["785848"],
                "vehicle_all": True,
                "vehicle_ids": [],
            },
        }
    )
    assert not permissions.can_write_user_status()


def test_status_manual_false_denies_user_status_writes() -> None:
    """Without status_manual the user status may not be written."""
    permissions = _permissions(
        {
            **FULL_ACCESS,
            "status_manual": False,
        }
    )
    assert not permissions.can_write_user_status()


def test_management_bypasses_all_checks() -> None:
    """Management access grants all write operations regardless of flags."""
    permissions = _permissions({"management": True})
    assert permissions.can_write_vehicle_status("113090")
    assert permissions.can_write_user_status()
    assert permissions.has_status_permission()


def test_missing_status_denies_status_view_and_writes() -> None:
    """Without status neither reads nor writes for status are granted."""
    permissions = _permissions(
        {
            **FULL_ACCESS,
            "status": False,
        }
    )
    assert not permissions.has_status_permission()
    assert not permissions.can_write_user_status()
    assert not permissions.can_write_vehicle_status("113090")


def test_empty_access_fails_open_for_reads_closed_for_writes() -> None:
    """Without any access data reads stay available, writes are denied."""
    permissions = _permissions({})
    assert permissions.has_status_permission()
    assert not permissions.can_write_user_status()
    assert not permissions.can_write_vehicle_status("113090")


def test_invalid_access_data_resets_cache() -> None:
    """Non-dict access data resets the permission cache."""
    permissions = DiveraPermissions()
    permissions.ucr_id = "641834"
    permissions.replace_permissions_from_ucr_data(
        {"data": {"user": {"access": FULL_ACCESS}}}
    )
    assert permissions.can_write_user_status()

    permissions.replace_permissions_from_ucr_data({"data": {"user": {}}})
    assert permissions.permissions == {}
    assert permissions.status_actions == {}
    assert not permissions.can_write_user_status()
    assert permissions.has_status_permission()


def test_has_permission_does_not_raise() -> None:
    """has_permission returns booleans instead of raising."""
    permissions = _permissions({"alarm": True})
    assert permissions.has_permission("alarm")
    assert not permissions.has_permission("news")
    try:
        permissions.check("news")
    except HomeAssistantError:
        pass
    else:
        raise AssertionError("check('news') should raise HomeAssistantError")
