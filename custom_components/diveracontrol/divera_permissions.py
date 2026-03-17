"""Divera permission handler."""

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .const import D_ACCESS, D_DATA, D_USER, PERM_MANAGEMENT

_LOGGER = logging.getLogger(__name__)


class DiveraPermissions:
    """Handles permissions for Divera API."""

    def __init__(self) -> None:
        """Initialize DiveraPermissions."""
        self.permissions: dict[str, bool] = {}
        self.ucr_id: str | None = None

    def replace_permissions_from_ucr_data(self, raw_ucr_data: dict[str, Any]) -> None:
        """Replace permission cache using current pull/all response data."""
        raw_access = raw_ucr_data.get(D_DATA, {}).get(D_USER, {}).get(D_ACCESS, {})

        if not isinstance(raw_access, dict):
            self.permissions = {}
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
        _LOGGER.debug(
            "Permission cache refreshed for cluster %s with %s entries",
            self.ucr_id,
            len(self.permissions),
        )

    def check(self, perm_key: str) -> None:
        """Raise when a permission is not granted by the current permission cache.

        This is used when we need to fail-fast if a permission is missing.
        Logging is handled by has_permission().

        Args:
            perm_key: The permission key to check for.

        Raises:
            HomeAssistantError: When permission is denied.

        """

        if not self.permissions:
            _LOGGER.debug(
                "No permission data available yet for cluster %s, permission '%s' denied",
                self.ucr_id,
                perm_key,
            )
            raise HomeAssistantError(
                f"No permission data available yet for cluster '{self.ucr_id}'"
            )

        if self.permissions.get(PERM_MANAGEMENT):
            _LOGGER.debug(
                "Management permission granted for cluster %s, bypassing specific permission check for '%s'",
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
