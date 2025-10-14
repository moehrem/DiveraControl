"""Support for Divera dynamic entities."""

import logging
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.core import callback
import homeassistant.helpers.entity_registry as er

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_MONITOR,
    D_OPEN_ALARMS,
    D_STATUS,
    D_VEHICLE,
    DOMAIN,
    I_AVAILABILITY,
    I_CLOSED_ALARM,
    I_COUNTER_ACTIVE_ALARMS,
    I_FIRESTATION,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_VEHICLE,
)
from .coordinator import DiveraCoordinator
from .entity import BaseDiveraEntity

_LOGGER = logging.getLogger(__name__)


class DiveraAlarmSensorManager(BaseDiveraEntity):
    """Manager for dynamic alarm sensors."""

    def __init__(
        self, coordinator: DiveraCoordinator, ucr_id: str, async_add_entities
    ) -> None:
        """Initialize alarm sensor manager."""
        super().__init__(coordinator)
        self._ucr_id = ucr_id
        self._async_add_entities = async_add_entities
        self._known_alarm_ids: set[str] = set()

    async def async_added_to_hass(self) -> None:
        """Register callbacks when added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # Initial update
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        current_alarm_ids = set(
            self.coordinator.data.get(D_ALARM, {}).get("items", {}).keys()
        )

        # Remove archived alarms
        archived_alarm_ids = self._known_alarm_ids - current_alarm_ids
        if archived_alarm_ids:
            entity_registry = er.async_get(self.hass)
            for alarm_id in archived_alarm_ids:
                unique_id = f"{self._ucr_id}_alarm_{alarm_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed alarm sensor: %s", alarm_id)
            self._known_alarm_ids.difference_update(archived_alarm_ids)

        # Add new alarms
        new_alarm_ids = current_alarm_ids - self._known_alarm_ids
        if new_alarm_ids:
            new_sensors = [
                DiveraAlarmSensor(self.coordinator, alarm_id)
                for alarm_id in new_alarm_ids
            ]
            self._async_add_entities(new_sensors, update_before_add=False)
            self._known_alarm_ids.update(new_alarm_ids)
            _LOGGER.debug("Added %d alarm sensors", len(new_alarm_ids))


class DiveraVehicleSensorManager(BaseDiveraEntity):
    """Manager for dynamic vehicle sensors."""

    def __init__(
        self, coordinator: DiveraCoordinator, ucr_id: str, async_add_entities
    ) -> None:
        """Initialize vehicle sensor manager."""
        super().__init__(coordinator)
        self._ucr_id = ucr_id
        self._async_add_entities = async_add_entities
        self._known_vehicle_ids: set[str] = set()

    async def async_added_to_hass(self) -> None:
        """Register callbacks when added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # Initial update
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        current_vehicle_ids = set(
            self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {}).keys()
        )

        # Remove archived vehicles
        archived_vehicle_ids = self._known_vehicle_ids - current_vehicle_ids
        if archived_vehicle_ids:
            entity_registry = er.async_get(self.hass)
            for vehicle_id in archived_vehicle_ids:
                unique_id = f"{self._ucr_id}_vehicle_{vehicle_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed vehicle sensor: %s", vehicle_id)
            self._known_vehicle_ids.difference_update(archived_vehicle_ids)

        # Add new vehicles
        new_vehicle_ids = current_vehicle_ids - self._known_vehicle_ids
        if new_vehicle_ids:
            new_sensors = [
                DiveraVehicleSensor(self.coordinator, vehicle_id)
                for vehicle_id in new_vehicle_ids
            ]
            self._async_add_entities(new_sensors, update_before_add=False)
            self._known_vehicle_ids.update(new_vehicle_ids)
            _LOGGER.debug("Added %d vehicle sensors", len(new_vehicle_ids))


class DiveraAvailabilitySensorManager(BaseDiveraEntity):
    """Manager for dynamic availability sensors."""

    def __init__(
        self, coordinator: DiveraCoordinator, ucr_id: str, async_add_entities
    ) -> None:
        """Initialize availability sensor manager."""
        super().__init__(coordinator)
        self._ucr_id = ucr_id
        self._async_add_entities = async_add_entities
        self._known_status_ids: set[str] = set()

    async def async_added_to_hass(self) -> None:
        """Register callbacks when added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # Initial update
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        current_status_ids = set(
            self.coordinator.data.get(D_CLUSTER, {}).get(D_STATUS, {}).keys()
        )

        # Remove archived statuses
        archived_status_ids = self._known_status_ids - current_status_ids
        if archived_status_ids:
            entity_registry = er.async_get(self.hass)
            for status_id in archived_status_ids:
                unique_id = f"{self._ucr_id}_availability_{status_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed availability sensor: %s", status_id)
            self._known_status_ids.difference_update(archived_status_ids)

        # Add new statuses
        new_status_ids = current_status_ids - self._known_status_ids
        if new_status_ids:
            new_sensors = [
                DiveraAvailabilitySensor(self.coordinator, status_id)
                for status_id in new_status_ids
            ]
            self._async_add_entities(new_sensors, update_before_add=False)
            self._known_status_ids.update(new_status_ids)
            _LOGGER.debug("Added %d availability sensors", len(new_status_ids))


class DiveraAlarmSensor(BaseDiveraEntity):
    """Sensor to represent a single alarm."""

    def __init__(self, coordinator: DiveraCoordinator, alarm_id: str) -> None:
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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._get_alarm_data() is not None

    @property
    def state(self) -> str:  # type: ignore[override]
        """Return the state of the alarm."""
        if alarm_data := self._get_alarm_data():
            return alarm_data.get("title", "Unknown")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return the extra state attributes of the alarm."""
        return self._get_alarm_data()

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return the icon of the alarm."""
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
        return None


class DiveraVehicleSensor(BaseDiveraEntity):
    """Sensor to represent a single vehicle."""

    def __init__(self, coordinator: DiveraCoordinator, vehicle_id: str) -> None:
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

    @property
    def available(self) -> bool:
        """Return availability of the vehicle."""
        return super().available and self._get_vehicle_data() is not None

    @property
    def state(self) -> str:  # type: ignore[override]
        """Return state of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            return vehicle_data.get("fmsstatus_id", "Unknown")
        return None

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return name of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            _shortname = vehicle_data.get("shortname", "Unknown")
            _veh_name = vehicle_data.get("name", "Unknown")
            return f"{_shortname} / {_veh_name}"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return extra state attributes of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            return {"vehicle_id": self.vehicle_id, **vehicle_data}
        return {}


class DiveraUnitSensor(BaseDiveraEntity):
    """Sensor to represent a divera-unit."""

    def __init__(self, coordinator: DiveraCoordinator, ucr_id: str) -> None:
        """Init class DiveraUnitSensor."""
        super().__init__(coordinator)

        cluster_data = coordinator.data.get(D_CLUSTER, {})
        self.cluster_shortname = cluster_data.get("shortname", "Unknown")
        self.cluster_address = cluster_data.get("address", {"error": "no address data"})

        # static entity attributes
        self._attr_name = self.cluster_name
        self.entity_id = f"sensor.{ucr_id}_cluster_address"
        self._attr_unique_id = f"{ucr_id}_cluster_address"
        self._attr_icon = I_FIRESTATION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> str:  # type: ignore[override]
        """Return the state."""
        return self.ucr_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return extra state attributes."""
        return {
            "ucr_id": self.ucr_id,
            "shortname": self.cluster_shortname,
            **self.cluster_address,
        }


class DiveraOpenAlarmsSensor(BaseDiveraEntity):
    """Sensor to count active alarms."""

    def __init__(self, coordinator: DiveraCoordinator, ucr_id: str) -> None:
        """Init class DiveraOpenAlarmsSensor."""
        super().__init__(coordinator)

        # static entity attributes
        self._attr_translation_key = "open_alarms"
        self.entity_id = f"sensor.{ucr_id}_open_alarms"
        self._attr_unique_id = f"{ucr_id}_open_alarms"
        self._attr_icon = I_COUNTER_ACTIVE_ALARMS

    @property
    def state(self) -> int:  # type: ignore[override]
        """Return number of open alarms."""
        return self.coordinator.data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)


class DiveraAvailabilitySensor(BaseDiveraEntity):
    """Sensor to return personal status."""

    def __init__(self, coordinator: DiveraCoordinator, status_id: str) -> None:
        """Init class DiveraAvailabilitySensor."""
        super().__init__(coordinator)

        self.status_id = status_id
        self.status_name = (
            coordinator.data.get(D_CLUSTER, {})
            .get(D_STATUS, {})
            .get(status_id, {})
            .get("name", "Unknown")
        )

        # static entity attributes
        self._attr_name = f"Status: {self.status_name}"
        self.entity_id = f"sensor.{self.ucr_id}_status_{self.status_id}"
        self._attr_unique_id = f"{self.ucr_id}_availability_{status_id}"
        self._attr_icon = I_AVAILABILITY

    @property
    def state(self) -> int:  # type: ignore[override]
        """Return the number of available members."""
        return (
            self.coordinator.data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("all", 0)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return the extra state attributes, which are the available qualifications."""
        _monitor_qualification_data = (
            self.coordinator.data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("qualification", {})
        )
        _cluster_qualification_data = self.coordinator.data.get(D_CLUSTER, {}).get(
            "qualification", {}
        )
        return {
            _cluster_qualification_data[key]["shortname"]: value
            for key, value in _monitor_qualification_data.items()
            if key in _cluster_qualification_data
        }
