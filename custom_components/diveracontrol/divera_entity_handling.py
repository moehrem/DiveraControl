"""Contains all base divera entity classes."""

import logging
from typing import Any

from homeassistant.helpers.entity import Entity
from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    # general
    DOMAIN,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    # data
    D_ALARM,
    D_OPEN_ALARMS,
    D_COORDINATOR,
    D_DATA,
    D_CLUSTER_ID,
    D_UCR,
    D_CLUSTER_NAME,
    D_CLUSTER,
    D_VEHICLE,
    D_UCR_ID,
    D_USER,
    D_STATUS,
    D_MONITOR,
    # icons
    I_CLOSED_ALARM,
    I_COUNTER_ACTIVE_ALARMS,
    I_FIRESTATION,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_AVAILABILITY,
    I_VEHICLE,
)

from .utils import get_device_info

_LOGGER = logging.getLogger(__name__)


class BaseDiveraEntity(CoordinatorEntity):
    """Gemeinsame Basisklasse für Sensoren und Tracker."""

    def __init__(self, coordinator) -> None:
        """Initialisiert die gemeinsame Basisklasse."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.cluster_data = coordinator.cluster_data
        self.cluster_id = coordinator.admin_data[D_CLUSTER_ID]
        self.cluster_name = coordinator.admin_data[D_CLUSTER_NAME]

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.cluster_name)

    @property
    def should_poll(self) -> bool:
        """Gibt an, dass die Entität nicht gepollt werden muss."""
        return False

    async def async_added_to_hass(self) -> None:
        """Registriert die Entität im Koordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def remove_from_hass(self) -> None:
        """Entfernt die Entität vollständig aus Home Assistant."""
        _LOGGER.debug("Starting removal process for entity: %s", self.entity_id)

        # Entferne aus dem Entity-Registry
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

        # Entferne aus der State-Machine
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


class BaseDiveraSensor(BaseDiveraEntity):
    """Basisklasse für Divera-Sensoren."""

    def __init__(self, coordinator) -> None:
        """Initialisiert einen Sensor."""
        super().__init__(coordinator)

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.cluster_name)


class DiveraAlarmSensor(BaseDiveraSensor):
    """Sensor to represent a single alarm."""

    def __init__(self, coordinator, alarm_id: str) -> None:
        """Init class DiveraAlarmSensor."""
        super().__init__(coordinator)
        self.alarm_id = alarm_id
        self.entity_id = f"sensor.{self.cluster_id}_alarm_{self.alarm_id}"

    @property
    def unique_id(self) -> str:
        """Unique ID of sensor."""
        return f"{self.cluster_id}_alarm_{self.alarm_id}"

    @property
    def name(self) -> str:
        """Name of sensor."""
        return f"Alarm {self.alarm_id}"

    @property
    def state(self) -> str:
        """State of sensor."""
        return (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("title", "Unknown")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        return (
            self.cluster_data.get(D_ALARM, {}).get("items", {}).get(self.alarm_id, {})
        )

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        closed = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("closed", False)
        )
        priority = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("priority", False)
        )
        if closed:
            return I_CLOSED_ALARM
        if priority:
            return I_OPEN_ALARM

        return I_OPEN_ALARM_NOPRIO


class DiveraVehicleSensor(BaseDiveraSensor):
    """Sensor to represent a single vehicle."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        """Init class DiveraVehicleSensor."""
        super().__init__(coordinator)
        self.vehicle_id = vehicle_id
        self.entity_id = f"sensor.{f'{self.cluster_id}_vehicle_{self.vehicle_id}'}"

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_vehicle_{self.vehicle_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique if if sensor."""
        return f"{self.cluster_id}_vehicle_{self.vehicle_id}"

    @property
    def name(self) -> str:
        """Name of sensor."""
        shortname = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("shortname", "Unknown")
        )
        veh_name = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("name", "Unknown")
        )
        return f"{shortname} / {veh_name}"

    @property
    def state(self) -> str:
        """State of sensor."""
        return (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("fmsstatus_id", "Unknown")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        extra_state_attributes = {}
        extra_state_attributes["vehicle_id"] = self.vehicle_id
        extra_state_attributes.update(
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
        )
        return extra_state_attributes

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_VEHICLE


class DiveraUnitSensor(BaseDiveraSensor):
    """Sensor to represent a divera-unit."""

    def __init__(self, coordinator) -> None:
        """Init class DiveraUnitSensor."""
        super().__init__(coordinator)
        self.entity_id = f"sensor.{self.cluster_id}_cluster_address"

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"{self.cluster_id}_cluster_address"

    @property
    def name(self) -> str:
        """Name of sensor."""
        return self.cluster_name

    @property
    def state(self) -> str:
        """State of sensor."""
        return self.cluster_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        cluster_shortname = self.cluster_data.get(D_CLUSTER, {}).get(
            "shortname", "Unknown"
        )
        cluster_address = self.cluster_data.get(D_CLUSTER, {}).get(
            "address", {"error": "no address data"}
        )
        return {
            "cluster_id": self.cluster_id,
            "shortname": cluster_shortname,
            **cluster_address,
        }

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_FIRESTATION


class DiveraOpenAlarmsSensor(BaseDiveraSensor):
    """Sensor to count active alarms."""

    def __init__(self, coordinator) -> None:
        """Init class DiveraOpenAlarmsSensor."""
        super().__init__(coordinator)
        self.entity_id = f"sensor.{self.cluster_id}_open_alarms"

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"{self.cluster_id}_open_alarms"

    @property
    def name(self) -> str:
        """Name of sensor."""
        return "Open Alarms"

    @property
    def state(self) -> int:
        """State of sensor."""
        return self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_COUNTER_ACTIVE_ALARMS


class DiveraAvailabilitySensor(BaseDiveraSensor):
    """Sensor to return personal status."""

    def __init__(self, coordinator: dict, status_id: str) -> None:
        """Init class DiveraAvailabilitySensor."""
        super().__init__(coordinator)
        self.status_id = status_id
        self.entity_id = f"sensor.{self.cluster_id}_status_{self.status_id}"

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"sensor.{self.cluster_id}_status_{self.status_id}"

    @property
    def name(self) -> str:
        """Name of sensor."""
        status_name = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_STATUS, {})
            .get(self.status_id, {})
            .get("name", "Unknown")
        )
        return f"Verfügbarkeit: {status_name}"

    @property
    def state(self) -> int:
        """State of sensor."""
        return (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("all", 0)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        monitor_qualification_data = (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("qualification", {})
        )
        cluster_qualification_data = self.cluster_data.get(D_CLUSTER, {}).get(
            "qualification", {}
        )
        return {
            cluster_qualification_data[key]["shortname"]: value
            for key, value in monitor_qualification_data.items()
            if key in cluster_qualification_data
        }

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_AVAILABILITY


class BaseDiveraTracker(TrackerEntity, BaseDiveraEntity):
    """Basisklasse für Divera-Tracker."""

    def __init__(self, coordinator) -> None:
        """Initialisiert einen Tracker."""
        TrackerEntity.__init__(self)
        BaseDiveraEntity.__init__(self, coordinator)

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.cluster_name)


class DiveraAlarmTracker(BaseDiveraTracker):
    """A device tracker for alarms."""

    def __init__(self, coordinator, alarm_id) -> None:
        """Initialize an alarm tracker."""
        super().__init__(coordinator)
        self.alarm_id = alarm_id
        self.entity_id = (
            f"device_tracker.{self.cluster_id}_alarmtracker_{self.alarm_id}"
        )

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.cluster_id}_alarmtracker_{self.alarm_id}"

    @property
    def name(self):
        """Return the name of the device tracker."""
        return f"Alarm {self.alarm_id}"

    @property
    def latitude(self):
        """Latitude of the tracker."""
        return (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("lat", 0)
        )

    @property
    def longitude(self):
        """Longitude of the tracker."""
        return (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("lng", 0)
        )

    @property
    def icon(self):
        """Return an icon for the tracker."""
        closed = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("closed", False)
        )
        priority = (
            self.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(self.alarm_id, {})
            .get("priority", False)
        )
        if closed:
            return I_CLOSED_ALARM
        elif priority:
            return I_OPEN_ALARM
        else:
            return I_OPEN_ALARM_NOPRIO


class DiveraVehicleTracker(BaseDiveraTracker):
    """A device tracker for vehicles."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator)
        self.vehicle_id = vehicle_id
        self.entity_id = (
            f"device_tracker.{self.cluster_id}_vehicletracker_{self.vehicle_id}"
        )

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.cluster_id}_vehicletracker_{self.vehicle_id}"

    @property
    def name(self):
        """Return the name of the device tracker."""
        shortname = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("shortname", "Unknown")
        )
        veh_name = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("name", "Unknown")
        )
        return f"{shortname} / {veh_name}"

    @property
    def latitude(self):
        """Latitude of the tracker."""

        return (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("lat", 0)
        )

    @property
    def longitude(self):
        """Longitude of the tracker."""
        return (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("lng", 0)
        )

    # @property
    # def extra_state_attributes(self):
    #     """Return additional attributes, including icon color."""
    #     vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
    #     status = str(
    #         vehicle_data.get("fmsstatus_id", "unknown")
    #     )  # Sicherstellen, dass es ein String ist

    #     color_map = {
    #         "1": "#55B300",  # Grün
    #         "2": "#198215",  # Dunkelgrün
    #         "3": "#FF460C",  # Orange-Rot
    #         "4": "#D60000",  # Rot
    #         "5": "#EFB200",  # Gelb
    #         "6": "#3E3E3E",  # Grau
    #         "7": "#0087E6",  # Blau
    #         "8": "#0038A9",  # Dunkelblau
    #         "9": "#001A7A",  # Navy
    #         "0": "#E400FF",  # Lila
    #     }

    #     return {
    #         "icon_color": color_map.get(status, "#808080"),  # Standard: Grau
    #     }

    @property
    def icon(self):
        """Return an icon for the tracker."""
        status = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self.vehicle_id, {})
            .get("fmsstatus_id", "unknown")
        )

        if status == "unknown":
            return "mdi:help-box"

        return f"mdi:numeric-{status}-box"
