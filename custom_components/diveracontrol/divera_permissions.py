"""Divera permission handler."""

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .const import (
    D_ACCESS,
    D_DATA,
    D_STATUS_ACTIONS,
    D_USER,
    PERM_MANAGEMENT,
    PERM_STATUS,
    PERM_STATUS_ACTION_SET_ALL,
    PERM_STATUS_ACTION_VEHICLE_ALL,
    PERM_STATUS_MANUAL,
    PERM_STATUS_VEHICLE,
)

_LOGGER = logging.getLogger(__name__)


class DiveraPermissions:
    """Handles permissions for Divera API."""

    def __init__(self) -> None:
        """Initialize DiveraPermissions."""
        self.permissions: dict[str, bool] = {}
        self.status_actions: dict[str, Any] = {}
        self.ucr_id: str | None = None

    def replace_permissions_from_ucr_data(self, raw_ucr_data: dict[str, Any]) -> None:
        """Replace permission cache using current pull/all response data."""
        raw_access = raw_ucr_data.get(D_DATA, {}).get(D_USER, {}).get(D_ACCESS, {})

        if not isinstance(raw_access, dict):
            self.permissions = {}
            self.status_actions = {}
            _LOGGER.debug(
                "Permission cache reset for cluster %s, access data missing or invalid",
                self.ucr_id,
            )
            return

        self.permissions = {
            key: bool(value)
            for key, value in raw_access.items()
            if isinstance(key, str)
        }
        raw_status_actions = raw_access.get(D_STATUS_ACTIONS, {})
        self.status_actions = (
            raw_status_actions if isinstance(raw_status_actions, dict) else {}
        )
        _LOGGER.debug(
            "Permission cache refreshed for cluster %s with %s entries",
            self.ucr_id,
            len(self.permissions),
        )

    def check(self, perm_key: str) -> None:
        """Raise when a permission is not granted by the current permission cache.

        This is used when we need to fail-fast if a permission is missing.
        Logging and error raising are handled directly by this method.

        Args:
            perm_key: The permission key to check for.

        Raises:
            HomeAssistantError: When permission is denied.

        """

        if not self.permissions:
            _LOGGER.debug(
                "No permission data available yet for cluster %s, permission '%s' "
                "denied",
                self.ucr_id,
                perm_key,
            )
            raise HomeAssistantError(
                f"No permission data available yet for cluster '{self.ucr_id}'"
            )

        if self.permissions.get(PERM_MANAGEMENT):
            _LOGGER.debug(
                "Management permission granted for cluster %s, bypassing specific "
                "permission check for '%s'",
                self.ucr_id,
                perm_key,
            )
            return

        has_perm = self.permissions.get(perm_key, False)
        if not has_perm:
            _LOGGER.debug(
                "Permission '%s' denied for cluster %s",
                perm_key,
                self.ucr_id,
            )
            raise HomeAssistantError(
                f"Permission '{perm_key}' denied for cluster '{self.ucr_id}'"
            )

    # ------------------------------------------------------------------
    # Granular permission helpers for status write access
    # ------------------------------------------------------------------

    def has_permission(self, perm_key: str) -> bool:
        """Return whether a permission is granted without raising.

        Args:
            perm_key: The permission key to check for.

        Returns:
            bool: True when the permission is granted, False otherwise.
        """
        try:
            self.check(perm_key)
        except HomeAssistantError:
            return False
        return True

    def can_write_vehicle_status(self, vehicle_id: str | int | None = None) -> bool:
        """Return whether the user may set the FMS status of a vehicle.

        Requires the ``status_vehicle`` access flag plus either
        ``status_actions.vehicle_all`` or the concrete vehicle in
        ``status_actions.vehicle_ids``. Management access bypasses both.

        Args:
            vehicle_id: Optional vehicle id for the ``vehicle_ids`` restriction.

        Returns:
            bool: True when the vehicle status may be written.
        """
        if self.has_permission(PERM_MANAGEMENT):
            return True
        if not self.has_permission(PERM_STATUS):
            return False
        if not self.has_permission(PERM_STATUS_VEHICLE):
            return False
        if self.status_actions.get(PERM_STATUS_ACTION_VEHICLE_ALL, False):
            return True
        if vehicle_id is None:
            return False
        allowed_ids = self.status_actions.get("vehicle_ids", [])
        if not isinstance(allowed_ids, list):
            return False
        return str(vehicle_id) in {str(item) for item in allowed_ids}

    def can_write_user_status(self) -> bool:
        """Return whether the user may set their own status.

        Requires the ``status`` and ``status_manual`` access flags plus
        ``status_actions.set_all`` or the user relation in
        ``status_actions.set_ids``. Management access bypasses all.

        Returns:
            bool: True when the user status may be written.
        """
        if self.has_permission(PERM_MANAGEMENT):
            return True
        if not self.has_permission(PERM_STATUS_MANUAL):
            return False
        if not self.has_permission(PERM_STATUS):
            return False
        if self.status_actions.get(PERM_STATUS_ACTION_SET_ALL, False):
            return True
        allowed_ids = self.status_actions.get("set_ids", [])
        if not isinstance(allowed_ids, list):
            return False
        return str(self.ucr_id) in {str(item) for item in allowed_ids}

    def has_status_permission(self) -> bool:
        """Return whether the user may view status information at all.

        Used to gate read-only availability sensors. When no permission
        data is available at all, view access is assumed (fail-open for
        read paths) to keep existing setups working.

        Returns:
            bool: True when status information may be viewed.
        """
        if not self.permissions:
            return True
        return self.has_permission(PERM_STATUS)
