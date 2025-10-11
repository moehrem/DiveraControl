"""Contains all base divera entity classes."""

import logging
from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_FMS_STATUS,
    D_MONITOR,
    D_OPEN_ALARMS,
    D_STATUS,
    D_VEHICLE,
    I_AVAILABILITY,
    I_CLOSED_ALARM,
    I_COUNTER_ACTIVE_ALARMS,
    I_FIRESTATION,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_VEHICLE,
)
from .utils import get_device_info

_LOGGER = logging.getLogger(__name__)


class BaseDiveraEntity(CoordinatorEntity):
    """Base class for DiveraControl entities."""

    def __init__(self, coordinator) -> None:
        """Init base class."""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self.cluster_data = coordinator.data
        self.ucr_id = coordinator.ucr_id
        self.cluster_name = coordinator.cluster_name

        self._attr_device_info = get_device_info(self.cluster_name)
        self._attr_should_poll = False
        self._attr_has_entity_name = True

    async def async_added_to_hass(self) -> None:
        """Register entity with coordinator."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def remove_from_hass(self) -> None:
        """Fully remove entity from HomeAssistant."""
        _LOGGER.debug("Starting removal process for entity: %s", self.entity_id)

        # remove from entity-registry
        try:
            registry = er.async_get(self.hass)
            if registry.async_is_registered(self.entity_id):
                registry.async_remove(self.entity_id)
                _LOGGER.debug("Removed entity from registry: %s", self.entity_id)
            else:
                _LOGGER.debug("Entity not found in registry: %s", self.entity_id)
        except Exception as e:
            _LOGGER.error(
                "Failed to remove entity from registry: %s, Error: %s",
                self.entity_id,
                e,
            )

        # remove from state machine
        try:
            self.hass.states.async_remove(self.entity_id)
            _LOGGER.debug("Removed entity from state machine: %s", self.entity_id)
        except Exception as e:
            _LOGGER.error(
                "Failed to remove entity from state machine: %s, Error: %s",
                self.entity_id,
                e,
            )

        _LOGGER.info("Entity successfully removed: %s", self.entity_id)


class DiveraAlarmSensor(BaseDiveraEntity):
    """Sensor to represent a single alarm."""

    def __init__(self, coordinator, alarm_id: str) -> None:
        """Init class DiveraAlarmSensor."""
        super().__init__(coordinator)

        self.alarm_id = alarm_id

        # static entity attributes
        self._attr_name = f"Alarm {self.alarm_id}"
        self.entity_id = f"sensor.{self.ucr_id}_alarm_{self.alarm_id}"
        self._attr_unique_id = f"{self.ucr_id}_alarm_{self.alarm_id}"

    def _get_alarm_data(self) -> dict[str, Any] | None:
        """Get alarm data safely, return None if alarm doesn't exist."""
        try:
            alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
            return alarm_items.get(self.alarm_id)
        except Exception:
            return None

    # dynamic entity attributes
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._get_alarm_data() is not None

    @property
    def state(self) -> str:  # type: ignore[override]
        """Return the state of the alarm."""
        if self._get_alarm_data():
            return (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("title", "Unknown")
            )
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return the extra state attributes of the alarm."""
        if self._get_alarm_data():
            return (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
            )
        return None

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return the icon of the alarm."""
        if self._get_alarm_data():
            _closed = (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("closed", False)
            )
            _priority = (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("priority", False)
            )

            return (
                I_CLOSED_ALARM
                if _closed
                else I_OPEN_ALARM
                if _priority
                else I_OPEN_ALARM_NOPRIO
            )
        return None


class DiveraVehicleSensor(BaseDiveraEntity):
    """Sensor to represent a single vehicle."""

    def __init__(
        self,
        coordinator,
        vehicle_id: str,
    ) -> None:
        """Init class DiveraVehicleSensor."""
        super().__init__(coordinator)

        self.vehicle_id = vehicle_id

        # static entity attributes
        self.entity_id = f"sensor.{self.ucr_id}_vehicle_{self.vehicle_id}"
        self._attr_unique_id = f"{self.ucr_id}_vehicle_{self.vehicle_id}"
        self._attr_icon = I_VEHICLE

    def _get_vehicle_data(self) -> dict[str, Any] | None:
        """Get vehicle data safely, return None if vehicle doesn't exist."""
        try:
            vehicle_items = self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
            return vehicle_items.get(self.vehicle_id)
        except Exception:
            return None

    # dynamic entity attributes
    @property
    def availability(self) -> str:  # type: ignore[override]
        """Return availability of the vehicle."""
        return super().available and self._get_vehicle_data() is not None

    @property
    def state(self) -> str:  # type: ignore[override]
        """Return state of the vehicle."""
        if self._get_vehicle_data():
            return (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("fmsstatus_id", "Unknown")
            )
        return None

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return name of the vehicle."""
        if self._get_vehicle_data():
            _shortname = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("shortname", "Unknown")
            )
            _veh_name = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("name", "Unknown")
            )
            return f"{_shortname} / {_veh_name}"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return extra state attributes of the vehicle."""
        _extra_state_attributes = {}
        if self._get_vehicle_data():
            _extra_state_attributes["vehicle_id"] = self.vehicle_id
            _extra_state_attributes.update(
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
            )
        return _extra_state_attributes


class DiveraUnitSensor(BaseDiveraEntity):
    """Sensor to represent a divera-unit."""

    def __init__(self, coordinator) -> None:
        """Init class DiveraUnitSensor."""
        super().__init__(coordinator)

        self.cluster_shortname = self.cluster_data.get(D_CLUSTER, {}).get(
            "shortname", "Unknown"
        )
        self.cluster_address = self.cluster_data.get(D_CLUSTER, {}).get(
            "address", {"error": "no address data"}
        )

        # static entity attributes
        self._attr_name = self.cluster_name
        self.entity_id = f"sensor.{self.ucr_id}_cluster_address"
        self._attr_unique_id = f"{self.ucr_id}_cluster_address"
        self._attr_state = self.ucr_id
        self._attr_extra_state_attributes = {
            "ucr_id": self.ucr_id,
            "shortname": self.cluster_shortname,
            **self.cluster_address,
        }
        self._attr_icon = I_FIRESTATION


class DiveraOpenAlarmsSensor(BaseDiveraEntity):
    """Sensor to count active alarms."""

    def __init__(self, coordinator) -> None:
        """Init class DiveraOpenAlarmsSensor."""
        super().__init__(coordinator)

        # static entity attributes
        self._attr_translation_key = "open_alarms"
        self.entity_id = f"sensor.{self.ucr_id}_open_alarms"
        self._attr_unique_id = f"{self.ucr_id}_open_alarms"
        self._attr_icon = I_COUNTER_ACTIVE_ALARMS

    @property
    def state(self) -> int:  # type: ignore[override]
        """Return number of open alarms."""
        return self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)


class DiveraAvailabilitySensor(BaseDiveraEntity):
    """Sensor to return personal status."""

    def __init__(self, coordinator: dict, status_id: str) -> None:
        """Init class DiveraAvailabilitySensor."""
        super().__init__(coordinator)

        self.status_id = status_id
        self.entity_id = f"sensor.{self.ucr_id}_status_{self.status_id}"
        self.status_name = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_STATUS, {})
            .get(self.status_id, {})
            .get("name", "Unknown")
        )

        # static entity attributes
        self._attr_name = f"Status: {self.status_name}"
        self.entity_id = f"sensor.{self.ucr_id}_status_{self.status_id}"
        # self._attr_unique_id = f"{self.ucr_id}_status_{self.status_id}"
        self._attr_unique_id = f"{self.ucr_id}_availability_{status_id}"
        self._attr_icon = I_AVAILABILITY

    # dynamic entity attributes
    @property
    def state(self) -> int:  # type: ignore[override]
        """Return the number of available members."""
        return (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("all", 0)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return the extra state attributes, which are the available qualifications."""
        _monitor_qualification_data = (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("qualification", {})
        )
        _cluster_qualification_data = self.cluster_data.get(D_CLUSTER, {}).get(
            "qualification", {}
        )
        return {
            _cluster_qualification_data[key]["shortname"]: value
            for key, value in _monitor_qualification_data.items()
            if key in _cluster_qualification_data
        }


class DiveraAlarmTracker(BaseDiveraEntity, TrackerEntity):  # type: ignore[misc]
    """A device tracker for alarms."""

    def __init__(self, coordinator, alarm_id) -> None:
        """Initialize an alarm tracker."""
        super().__init__(coordinator)

        self.alarm_id = alarm_id

        # static entity attributes
        self._attr_name = f"Alarm {self.alarm_id}"
        self.entity_id = f"device_tracker.{self.ucr_id}_alarmtracker_{self.alarm_id}"
        self._attr_unique_id = f"{self.ucr_id}_alarmtracker_{self.alarm_id}"

    def _get_alarm_data(self) -> dict[str, Any] | None:
        """Get alarm data safely, return None if alarm doesn't exist."""
        try:
            alarm_items = self.coordinator.data.get(D_ALARM, {}).get("items", {})
            return alarm_items.get(self.alarm_id)
        except Exception:
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._get_alarm_data() is not None

    # dynamic state attributes
    @property
    def latitude(self) -> float | None:  # type: ignore[override]
        "Return latitude of the alarm location."
        if self._get_alarm_data():
            return (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("lat", 0)
            )
        return None

    @property
    def longitude(self) -> float | None:  # type: ignore[override]
        "Return longitude of the alarm location."
        if self._get_alarm_data():
            return (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("lng", 0)
            )
        return None

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return icon of the alarm."""
        if self._get_alarm_data():
            _closed = (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("closed", False)
            )
            _priority = (
                self.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(self.alarm_id, {})
                .get("priority", False)
            )
            return (
                I_CLOSED_ALARM
                if _closed
                else I_OPEN_ALARM
                if _priority
                else I_OPEN_ALARM_NOPRIO
            )
        return None


class DiveraVehicleTracker(BaseDiveraEntity, TrackerEntity):  # type: ignore[misc]
    """A device tracker for vehicles."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        """Init device tracker class."""
        super().__init__(coordinator)

        self.vehicle_id = vehicle_id

        # static entity attributes
        self.entity_id = (
            f"device_tracker.{self.ucr_id}_vehicletracker_{self.vehicle_id}"
        )
        self._attr_unique_id = f"{self.ucr_id}_vehicletracker_{self.vehicle_id}"

    def _get_vehicle_data(self) -> dict[str, Any] | None:
        """Get vehicle data safely, return None if vehicle doesn't exist."""
        try:
            vehicle_items = self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
            return vehicle_items.get(self.vehicle_id)
        except Exception:
            return None

    # dynamic state attributes
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._get_vehicle_data() is not None

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return name of the vehicle."""
        if self._get_vehicle_data():
            _shortname = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("shortname", "Unknown")
            )
            _veh_name = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("name", "Unknown")
            )
            return f"{_shortname} / {_veh_name}"
        return None

    @property
    def latitude(self) -> float | None:  # type: ignore[override]
        """Return the latitude of the vehicle position."""
        if self._get_vehicle_data():
            return (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("lat", 0)
            )
        return None

    @property
    def longitude(self) -> float | None:  # type: ignore[override]
        """Return the longitude of the vehicle position."""
        if self._get_vehicle_data():
            return (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("lng", 0)
            )
        return None

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return icon of the vehicle tracker."""
        if self._get_vehicle_data():
            _veh_status = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("fmsstatus_id", "unknown")
            )
            return (
                "mdi:help-box"
                if _veh_status == "unknown"
                else f"mdi:numeric-{_veh_status}-box"
            )
        return None

    @property
    def extra_state_attributes(self):  # type: ignore[override]
        """Return extra state attributes for vehicle tracker."""
        if not self._get_vehicle_data():
            extra_state_attributes = {}
            _fms_items = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_FMS_STATUS, {})
                .get("items", {})
            )
            _veh_status = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(self.vehicle_id, {})
                .get("fmsstatus_id", "unknown")
            )
            extra_state_attributes["icon_color"] = _fms_items.get(
                str(_veh_status), {}
            ).get("color_hex", "#FF0000")

            return extra_state_attributes

        return None
