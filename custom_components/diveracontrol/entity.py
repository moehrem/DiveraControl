"""Contains all base divera entity classes."""

import logging

from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_NAME,
    D_MONITOR,
    D_OPEN_ALARMS,
    D_STATUS,
    D_UCR_ID,
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
        self.cluster_data = coordinator.cluster_data
        self.ucr_id = coordinator.admin_data[D_UCR_ID]
        self.cluster_name = coordinator.admin_data[D_CLUSTER_NAME]

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
        self.entity_id = f"sensor.{self.ucr_id}_alarm_{self.alarm_id}"
        self.closed = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("closed", False)
        )
        self.priority = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("priority", False)
        )

        # HA attributes
        self._attr_name = f"Alarm {self.alarm_id}"
        self.entity_id = f"sensor.{self.ucr_id}_alarm_{self.alarm_id}"
        self._attr_unique_id = f"{self.ucr_id}_alarm_{self.alarm_id}"
        self._attr_state = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("title", "Unknown")
        )
        self._attr_extra_state_attributes = (
            self.cluster_data.get(D_ALARM, {}).get("items", {}).get(self.alarm_id, {})
        )
        self._attr_icon = (
            I_CLOSED_ALARM
            if self.closed
            else I_OPEN_ALARM
            if self.priority
            else I_OPEN_ALARM_NOPRIO
        )


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
        self.entity_id = f"sensor.{f'{self.ucr_id}_vehicle_{self.vehicle_id}'}"
        self.shortname = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("shortname", "Unknown")
        )
        self.veh_name = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("name", "Unknown")
        )
        # building extra state attributes
        self._extra_state_attributes = {}
        self._extra_state_attributes["vehicle_id"] = self.vehicle_id
        self._extra_state_attributes.update(
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
        )

        # HA attributes
        self._attr_name = f"{self.shortname} / {self.veh_name}"
        self.entity_id = f"sensor.{self.ucr_id}_vehicle_{self.vehicle_id}"
        self._attr_unique_id = f"{self.ucr_id}_vehicle_{self.vehicle_id}"
        self._attr_state = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("fmsstatus_id", "Unknown")
        )
        self._attr_extra_state_attributes = self._extra_state_attributes
        self._attr_icon = I_VEHICLE


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

        # HA attributes
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

        # HA attributes
        self._attr_translation_key = "open_alarms"
        self.entity_id = f"sensor.{self.ucr_id}_open_alarms"
        self._attr_unique_id = f"{self.ucr_id}_open_alarms"
        self._attr_state = self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)
        self._attr_icon = I_COUNTER_ACTIVE_ALARMS


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

        # creating extra state attributes
        self._monitor_qualification_data = (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("qualification", {})
        )
        self._cluster_qualification_data = self.cluster_data.get(D_CLUSTER, {}).get(
            "qualification", {}
        )
        self._extra_state_attributes = {
            self._cluster_qualification_data[key]["shortname"]: value
            for key, value in self._monitor_qualification_data.items()
            if key in self._cluster_qualification_data
        }

        # HA attributes
        self._attr_name = f"Status: {self.status_name}"
        self.entity_id = f"sensor.{self.ucr_id}_status_{self.status_id}"
        self._attr_unique_id = f"{self.ucr_id}_status_{self.status_id}"
        self._attr_state = (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("all", 0)
        )
        self._attr_extra_state_attributes = self._extra_state_attributes
        self._attr_icon = I_AVAILABILITY


class DiveraAlarmTracker(BaseDiveraEntity, TrackerEntity):  # type: ignore[misc]
    """A device tracker for alarms."""

    def __init__(self, coordinator, alarm_id) -> None:
        """Initialize an alarm tracker."""
        super().__init__(coordinator)

        self.alarm_id = alarm_id
        self.closed = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("closed", False)
        )
        self.priority = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("priority", False)
        )

        # HA attributes
        self._attr_name = f"Alarm {self.alarm_id}"
        self.entity_id = f"device_tracker.{self.ucr_id}_alarmtracker_{self.alarm_id}"
        self._attr_unique_id = f"{self.ucr_id}_alarmtracker_{self.alarm_id}"
        self._attr_latitude = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("lat", 0)
        )
        self._attr_longitude = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("lng", 0)
        )
        self._attr_icon = (
            I_CLOSED_ALARM
            if self.closed
            else I_OPEN_ALARM
            if self.priority
            else I_OPEN_ALARM_NOPRIO
        )


class DiveraVehicleTracker(BaseDiveraEntity, TrackerEntity):  # type: ignore[misc]
    """A device tracker for vehicles."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        """Init device tracker class."""
        super().__init__(coordinator)

        self.vehicle_id = vehicle_id
        self.shortname = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("shortname", "Unknown")
        )
        self.veh_name = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("name", "Unknown")
        )
        self.veh_status = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("fmsstatus_id", "unknown")
        )

        # HA attributes
        self._attr_name = f"{self.shortname} / {self.veh_name}"
        self.entity_id = (
            f"device_tracker.{self.ucr_id}_vehicletracker_{self.vehicle_id}"
        )
        self._attr_unique_id = f"{self.ucr_id}_vehicletracker_{self.vehicle_id}"
        self._attr_latitude = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("lat", 0)
        )
        self._attr_longitude = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("lng", 0)
        )
        self._attr_icon = (
            "mdi:help-box"
            if self.veh_status == "unknown"
            else f"mdi:numeric-{self.veh_status}-box"
        )
