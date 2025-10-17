"""Support for Divera device tracker entities."""

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_FMS_STATUS,
    D_VEHICLE,
    DOMAIN,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
)
from .coordinator import DiveraCoordinator
from .entity import BaseDiveraEntity

_LOGGER = logging.getLogger(__name__)


class DiveraAlarmTrackerManager:
    """Manager for dynamic alarm trackers (helper object, not an Entity)."""

    def __init__(
        self,
        coordinator: DiveraCoordinator,
        ucr_id: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize alarm tracker manager."""
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._ucr_id = ucr_id
        self._async_add_entities = async_add_entities
        self._known_alarm_ids: set[str] = set()
        self._unsub: Callable[[], None] | None = None

    def start(self) -> None:
        """Register coordinator listener and run initial update."""
        if self._unsub is not None:
            return
        self._unsub = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        self._handle_coordinator_update()

    def stop(self) -> None:
        """Unregister coordinator listener if set."""
        if self._unsub:
            try:
                self._unsub()
            finally:
                self._unsub = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        current_alarm_ids = set(
            self.coordinator.data.get(D_ALARM, {}).get("items", {}).keys()
        )

        # Remove archived alarm trackers
        archived_alarm_ids = self._known_alarm_ids - current_alarm_ids
        if archived_alarm_ids:
            entity_registry = er.async_get(self.hass)
            for alarm_id in archived_alarm_ids:
                unique_id = f"{self._ucr_id}_alarmtracker_{alarm_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "device_tracker", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed alarm tracker: %s", alarm_id)
            self._known_alarm_ids.difference_update(archived_alarm_ids)

        # Add new alarm trackers
        new_alarm_ids = current_alarm_ids - self._known_alarm_ids
        if new_alarm_ids:
            new_trackers = [
                DiveraAlarmTracker(self.coordinator, alarm_id)
                for alarm_id in new_alarm_ids
            ]
            self._async_add_entities(new_trackers, update_before_add=False)
            self._known_alarm_ids.update(new_alarm_ids)
            _LOGGER.debug("Added %d alarm trackers", len(new_alarm_ids))


class DiveraVehicleTrackerManager:
    """Manager for dynamic vehicle trackers (helper object)."""

    def __init__(
        self,
        coordinator: DiveraCoordinator,
        ucr_id: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize vehicle tracker manager."""
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._ucr_id = ucr_id
        self._async_add_entities = async_add_entities
        self._known_vehicle_ids: set[str] = set()
        self._unsub: Callable[[], None] | None = None

    def start(self) -> None:
        """Register listener and perform initial sync."""
        if self._unsub is not None:
            return
        self._unsub = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        self._handle_coordinator_update()

    def stop(self) -> None:
        """Unregister listener."""
        if self._unsub:
            try:
                self._unsub()
            finally:
                self._unsub = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        current_vehicle_ids = set(
            self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {}).keys()
        )

        # Remove archived vehicle trackers
        archived_vehicle_ids = self._known_vehicle_ids - current_vehicle_ids
        if archived_vehicle_ids:
            entity_registry = er.async_get(self.hass)
            for vehicle_id in archived_vehicle_ids:
                unique_id = f"{self._ucr_id}_vehicletracker_{vehicle_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "device_tracker", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed vehicle tracker: %s", vehicle_id)
            self._known_vehicle_ids.difference_update(archived_vehicle_ids)

        # Add new vehicle trackers
        new_vehicle_ids = current_vehicle_ids - self._known_vehicle_ids
        if new_vehicle_ids:
            new_trackers = [
                DiveraVehicleTracker(self.coordinator, vehicle_id)
                for vehicle_id in new_vehicle_ids
            ]
            self._async_add_entities(new_trackers, update_before_add=False)
            self._known_vehicle_ids.update(new_vehicle_ids)
            _LOGGER.debug("Added %d vehicle trackers", len(new_vehicle_ids))


# === Individual Tracker Classes (update existing classes) ===


class DiveraAlarmTracker(BaseDiveraEntity, TrackerEntity):  # type: ignore[misc]
    """A device tracker for alarms."""

    def __init__(self, coordinator: DiveraCoordinator, alarm_id: str) -> None:
        """Initialize an alarm tracker."""
        super().__init__(coordinator)

        self.alarm_id = alarm_id

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_name = f"Alarm {self.alarm_id}"
        self.entity_id = f"device_tracker.{self.ucr_id}_alarmtracker_{self.alarm_id}"
        self._attr_unique_id = f"{self.ucr_id}_alarmtracker_{self.alarm_id}"

    def _get_alarm_data(self) -> dict[str, Any] | None:
        """Get alarm data safely, return None if alarm doesn't exist."""
        try:
            alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
            return alarm_items.get(self.alarm_id)
        except KeyError:
            return None

    @property  # type: ignore[override]
    def available(self) -> bool:  # type: ignore[override]
        """Return if entity is available."""
        return super().available and self._get_alarm_data() is not None

    @property
    def latitude(self) -> float | None:  # type: ignore[override]
        """Return latitude of the alarm location."""
        if alarm_data := self._get_alarm_data():
            return alarm_data.get("lat", 0)
        return None

    @property
    def longitude(self) -> float | None:  # type: ignore[override]
        """Return longitude of the alarm location."""
        if alarm_data := self._get_alarm_data():
            return alarm_data.get("lng", 0)
        return None

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return icon of the alarm."""
        if alarm_data := self._get_alarm_data():
            _closed = alarm_data.get("closed", False)
            _priority = alarm_data.get("priority", False)
            return (
                I_CLOSED_ALARM
                if _closed
                else I_OPEN_ALARM
                if _priority
                else I_OPEN_ALARM_NOPRIO
            )
        return I_OPEN_ALARM_NOPRIO


class DiveraVehicleTracker(BaseDiveraEntity, TrackerEntity):  # type: ignore[misc]
    """A device tracker for vehicles."""

    def __init__(self, coordinator: DiveraCoordinator, vehicle_id: str) -> None:
        """Init device tracker class."""
        super().__init__(coordinator)

        self.vehicle_id = vehicle_id

        # static entity attributes
        self._attr_has_entity_name = False
        self.entity_id = (
            f"device_tracker.{self.ucr_id}_vehicletracker_{self.vehicle_id}"
        )
        self._attr_unique_id = f"{self.ucr_id}_vehicletracker_{self.vehicle_id}"

    def _get_vehicle_data(self) -> dict[str, Any] | None:
        """Get vehicle data safely, return None if vehicle doesn't exist."""
        try:
            vehicle_items = self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
            return vehicle_items.get(self.vehicle_id)
        except KeyError:
            return None

    @property  # type: ignore[override]
    def available(self) -> bool:  # type: ignore[override]
        """Return if entity is available."""
        return super().available and self._get_vehicle_data() is not None

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return name of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            _shortname = vehicle_data.get("shortname", "Unknown")
            _veh_name = vehicle_data.get("name", "Unknown")
            return f"{_shortname} / {_veh_name}"
        return "Unknown Vehicle"

    @property
    def latitude(self) -> float | None:  # type: ignore[override]
        """Return the latitude of the vehicle position."""
        if vehicle_data := self._get_vehicle_data():
            return vehicle_data.get("lat", 0)
        return None

    @property
    def longitude(self) -> float | None:  # type: ignore[override]
        """Return the longitude of the vehicle position."""
        if vehicle_data := self._get_vehicle_data():
            return vehicle_data.get("lng", 0)
        return None

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return icon of the vehicle tracker."""
        if vehicle_data := self._get_vehicle_data():
            _veh_status = vehicle_data.get("fmsstatus_id", "unknown")
            return (
                "mdi:help-box"
                if _veh_status == "unknown"
                else f"mdi:numeric-{_veh_status}-box"
            )
        return "mdi:help-box"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return extra state attributes for vehicle tracker."""
        if vehicle_data := self._get_vehicle_data():
            _fms_items = (
                self.coordinator.data.get(D_CLUSTER, {})
                .get(D_FMS_STATUS, {})
                .get("items", {})
            )
            _veh_status = vehicle_data.get("fmsstatus_id", "unknown")
            icon_color = _fms_items.get(str(_veh_status), {}).get(
                "color_hex", "#FF0000"
            )

            return {"icon_color": icon_color}
        return {}
