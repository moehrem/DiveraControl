"""Support for Divera select entities."""

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import D_CLUSTER, D_STATUS, DOMAIN, I_AVAILABILITY
from .coordinator import DiveraCoordinator
from .entity import BaseDiveraEntity


class DiveraUserStatusSelect(BaseDiveraEntity, SelectEntity):
    """Select entity to set the user status."""

    _attr_has_entity_name = True
    _attr_translation_key = "user_status"
    _attr_icon = I_AVAILABILITY
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Initialize user status select entity."""
        super().__init__(coordinator)

        self._selected_status_id: str | None = None
        self.entity_id = f"select.{self.ucr_id}_user_status"
        self._attr_unique_id = f"{self.ucr_id}_user_status"

    def _get_status_items(self) -> dict[str, dict[str, Any]]:
        """Get user status mapping from coordinator data."""
        statuses = self.coordinator.data.get(D_CLUSTER, {}).get(D_STATUS, {})
        return {str(key): value for key, value in statuses.items()}

    def _status_label(self, status_id: str) -> str:
        """Return the user-facing label for a status option."""
        status = self._get_status_items().get(status_id, {})
        return str(status.get("name", status_id))

    def _option_to_status_id(self, option: str) -> str | None:
        """Map displayed select option back to status id."""
        for status_id, status in self._get_status_items().items():
            if option == str(status.get("name", status_id)):
                return status_id
        return None

    def _current_status_id_from_user(self) -> str | None:
        """Get current status ID from user data using known field variants."""
        user_data = self.coordinator.data.get("status", {})
        status_id = user_data.get("status_id")
        if status_id is None:
            return None
        return str(status_id)

    def _get_device_id(self) -> str | None:
        """Resolve the Home Assistant device_id for this entity."""
        registry = er.async_get(self.hass)
        entity_entry = registry.async_get(self.entity_id)
        if entity_entry is None:
            return None
        return entity_entry.device_id

    @property
    def options(self) -> list[str]:
        """Return available select options."""
        return [self._status_label(status_id) for status_id in self._get_status_items()]

    @property
    def current_option(self) -> str | None:
        """Return currently selected option."""
        if self._selected_status_id is not None:
            return self._status_label(self._selected_status_id)

        current_id = self._current_status_id_from_user()
        if current_id is None:
            return None

        return self._status_label(current_id)

    async def async_select_option(self, option: str) -> None:
        """Select a user status and trigger the user status service."""
        status_id = self._option_to_status_id(option)
        if status_id is None:
            raise HomeAssistantError(f"Unknown user status option selected: {option}")

        device_id = self._get_device_id()
        if not device_id:
            raise HomeAssistantError(
                "Could not resolve device_id for user status select"
            )

        await self.hass.services.async_call(
            DOMAIN,
            "post_user_status",
            {"device_id": device_id, "ucr_id": self.ucr_id, "id": int(status_id)},
            blocking=True,
        )

        self._selected_status_id = status_id
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

    def select_option(self, option: str) -> None:
        """Select option fallback for sync context.

        Home Assistant should call `async_select_option` for this entity.
        """
        raise NotImplementedError
