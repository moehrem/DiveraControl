"""Support for Divera select entities."""

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import (
    D_CLUSTER,
    D_STATUS,
    D_VEHICLE,
    DOMAIN,
    I_AVAILABILITY,
    I_VEHICLE,
    PERM_STATUS_USER,
)
from .coordinator import DiveraCoordinator
from .entity import BaseDiveraEntity


class DiveraUserStatusSelect(BaseDiveraEntity, SelectEntity):
    """Select entity to set the user status."""

    _attr_has_entity_name = True
    _attr_icon = I_AVAILABILITY

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Initialize user status select entity."""
        super().__init__(coordinator)

        self._selected_status_id: str | None = None
        self.entity_id = f"select.{self.ucr_id}_user_status"
        self._attr_unique_id = f"{self.ucr_id}_user_status"
        self._attr_entity_registry_enabled_default = self._user_status_permitted()

    def _user_status_permitted(self) -> bool:
        """Return whether the user may set their own status in Divera."""
        if self.coordinator.api is None:
            return False
        return self.coordinator.api.permissions.is_permitted(PERM_STATUS_USER)

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
            {"device_id": device_id, "id": int(status_id)},
            blocking=True,
        )

        self._selected_status_id = status_id
        self.async_write_ha_state()

    # def select_option(self, option: str) -> None:
    #     """Select option fallback for sync context.

    #     Home Assistant should call `async_select_option` for this entity.
    #     """
    #     raise NotImplementedError


class DiveraVehicleStatusSelect(BaseDiveraEntity, SelectEntity):
    """Select entity to set the FMS status of a single vehicle.

    Provides dynamic, vehicle-specific selection of the FMS status in the
    GUI and allows two-way communication by pushing status changes back to
    Divera via the ``post_vehicle_status`` service.
    """

    def __init__(self, coordinator: DiveraCoordinator, vehicle_id: str) -> None:
        """Initialize vehicle status select entity."""
        super().__init__(coordinator)

        self.vehicle_id = vehicle_id

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{self.ucr_id}_vehicle_status_{self.vehicle_id}"
        self.entity_id = f"select.{self.ucr_id}_vehicle_status_{self.vehicle_id}"
        self._attr_icon = I_VEHICLE

    def _get_vehicle_data(self) -> dict[str, Any] | None:
        """Get vehicle data safely, return None if vehicle doesn't exist."""
        vehicle_items = self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
        return vehicle_items.get(self.vehicle_id)

    def _get_fms_status_items(self) -> dict[str, dict[str, Any]]:
        """Get FMS status items keyed by status id (fmsstatus_id)."""
        items = (
            self.coordinator.data.get(D_CLUSTER, {})
            .get("fms_status", {})
            .get("items", {})
        )
        return {str(item_id): item for item_id, item in items.items()}

    def _status_option(self, status_id: str) -> str:
        """Return the display option for a FMS status id."""
        item = self._get_fms_status_items().get(status_id)
        if item is None:
            return status_id
        return f"{item.get('number')} - {item.get('name')}"

    def _option_to_status_id(self, option: str) -> str | None:
        """Map a displayed option back to the FMS status id."""
        for status_id in self._get_fms_status_items():
            if option == self._status_option(status_id):
                return status_id
        return None

    def _get_device_id(self) -> str | None:
        """Resolve the Home Assistant device_id for this entity."""
        registry = er.async_get(self.hass)
        entity_entry = registry.async_get(self.entity_id)
        if entity_entry is None:
            return None
        return entity_entry.device_id

    @property
    def name(self) -> str:
        """Return name of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            _shortname = vehicle_data.get("shortname", "Unknown")
            _veh_name = vehicle_data.get("name", "Unknown")
            return f"{_shortname} / {_veh_name}"
        return "Unknown Vehicle"

    @property
    def available(self) -> bool:
        """Return availability of the vehicle."""
        if super().available and self._get_vehicle_data() is not None:
            return True
        return False

    @property
    def options(self) -> list[str]:
        """Return the selectable FMS status options."""
        return [self._status_option(sid) for sid in self._get_fms_status_items()]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected FMS status option."""
        if vehicle_data := self._get_vehicle_data():
            status_id = vehicle_data.get("fmsstatus_id")
            if status_id is None:
                return None
            return self._status_option(str(status_id))
        return None

    async def async_select_option(self, option: str) -> None:
        """Push a newly selected FMS status to Divera."""
        device_id = self._get_device_id()
        if not device_id:
            raise HomeAssistantError(
                "Could not resolve device_id for vehicle status select"
            )
        status_id_str = self._option_to_status_id(option)
        if status_id_str is None:
            raise HomeAssistantError(
                f"Unknown vehicle status option selected: {option}"
            )

        await self.hass.services.async_call(
            DOMAIN,
            "post_vehicle_status",
            {
                "device_id": device_id,
                "vehicle": self.vehicle_id,
                "status": int(status_id_str),
            },
            blocking=True,
        )
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
