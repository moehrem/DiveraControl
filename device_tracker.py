"""Handles all device_tracker entities."""

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er

from .utils import sanitize_entity_id
from .const import (
    D_ALARM,
    D_COORDINATOR,
    D_CLUSTER_ADDRESS,
    D_CLUSTER_ID,
    D_VEHICLE,
    D_UCR,
    D_USER,
    DOMAIN,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_VEHICLE,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up Divera device trackers."""

    # return

    cluster = config_entry.data
    cluster_id = cluster[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    async def sync_sensors():
        """Synchronize all trackers with the current data from coordinator."""

        new_trackers = []

        for ucr_id, ucr_data in coordinator.data.items():
            ucr_alarm_data = ucr_data.get(D_ALARM, {})
            ucr_vehicle_data = ucr_data.get(D_VEHICLE, {})

            entity_registry = er.async_get(hass)

            # fetch registered trackers
            current_trackers = {
                entity.entity_id: entity
                for entity in entity_registry.entities.values()
                if entity.platform == DOMAIN
                and entity.domain == "device_tracker"
                and entity.unique_id.startswith(f"{ucr_id}_")
            }
            active_alarms = {
                sensor_id
                for sensor_id in current_trackers
                if f"device_tracker.{ucr_id}_alarm_" in sensor_id
            }

            active_vehicles = {
                vehicle_id
                for vehicle_id in current_trackers
                if f"device_tracker.{ucr_id}_vehicle_" in vehicle_id
            }

            # Add new alarm trackers
            active_alarm_ids = {sensor_id.split("_")[-1] for sensor_id in active_alarms}
            new_alarm_tracker = {
                alarm_id
                for alarm_id in ucr_alarm_data
                if alarm_id not in active_alarm_ids
            }

            for alarm_id in new_alarm_tracker:
                sensor = DiveraAlarmTracker(coordinator, ucr_data, alarm_id, ucr_id)
                _LOGGER.debug("Adding alarm sensor: %s", alarm_id)
                new_trackers.append(sensor)
                # current_sensors[alarm_id] = sensor

            # Add new vehicle sensors
            active_vehicle_ids = {
                vehicle_id.split("_")[-1] for vehicle_id in active_vehicles
            }
            new_vehicle_trackers = {
                vehicle_id
                for vehicle_id in ucr_vehicle_data
                if vehicle_id not in active_vehicle_ids
            }
            for vehicle_id in new_vehicle_trackers:
                sensor = DiveraVehicleTracker(coordinator, ucr_data, vehicle_id, ucr_id)
                _LOGGER.debug("Adding vehicle sensor: %s", vehicle_id)
                new_trackers.append(sensor)
                # current_sensors[vehicle_id] = sensor

            # remove outdated sensors
            active_sensor_ids = active_alarm_ids | active_vehicle_ids

            old_sensors = {
                sensor_id
                for sensor_id in active_sensor_ids
                if sensor_id not in ucr_alarm_data and sensor_id not in ucr_vehicle_data
            }

            removed_trackers = {
                sensor_id
                for sensor_id in current_trackers
                if any(entity_id in sensor_id for entity_id in old_sensors)
            }

            _LOGGER.debug("Current sensors: %s", list(current_trackers.keys()))
            _LOGGER.debug("Active alarm tracker: %s", active_alarms)
            _LOGGER.debug("Active vehicle tracker: %s", active_vehicles)
            _LOGGER.debug("All active tracker IDs: %s", current_trackers)
            _LOGGER.debug("Trackers that should be removed: %s", removed_trackers)

            for sensor_id in removed_trackers:
                if entity_registry.async_is_registered(sensor_id):
                    entity_registry.async_remove(sensor_id)
                    _LOGGER.debug("Removed sensor: %s", sensor_id)
                else:
                    _LOGGER.warning(
                        "Sensor not found in entity registry: %s", sensor_id
                    )

        # Add new sensors to Home Assistant
        if new_trackers:
            async_add_entities(new_trackers)

    # Initial synchronization
    await sync_sensors()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


class BaseDiveraTracker(TrackerEntity):
    """Base class for Divera device trackers."""

    def __init__(self, coordinator, ucr_data, ucr_id):
        """Initialize the device tracker."""
        self.coordinator = coordinator
        self.cluster_id = coordinator.cluster_id
        self.ucr_data = ucr_data
        self.ucr_id = ucr_id

    @property
    def device_info(self):
        """Return device information for the sensor."""
        self.firstname = self.ucr_data.get(D_USER, {}).get("firstname", "")
        self.lastname = self.ucr_data.get(D_USER, {}).get("lastname", "")
        return {
            "identifiers": {(DOMAIN, f"{self.firstname} {self.lastname}")},
            "name": f"{self.firstname} {self.lastname}",
            "manufacturer": MANUFACTURER,
            "model": DOMAIN,
            "sw_version": f"{VERSION}.{MINOR_VERSION}",
            "entry_type": "service",
        }

    @property
    def should_poll(self):
        """Indicate that the entity does not require polling."""
        return False

    async def async_added_to_hass(self) -> None:
        """Register updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self) -> None:
        """Fordere ein Update vom Koordinator an."""
        await self.coordinator.async_request_refresh()

    async def remove_from_hass(self) -> None:
        """Vollständige Entfernung der Entität aus Home Assistant."""
        _LOGGER.debug("Starting removal process for entity: %s", self.entity_id)

        # 1. Entferne die Entität aus dem Entity Registry
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

        # 2. Entferne die Entität aus dem State Machine
        try:
            self.hass.states.async_remove(self.entity_id)
            _LOGGER.debug("Removed entity from state machine: %s", self.entity_id)
        except Exception as e:
            _LOGGER.error(
                "Failed to remove entity from state machine: %s, Error: %s",
                self.entity_id,
                e,
            )

        # 3. Entferne die Entität aus internen Datenstrukturen
        try:
            if DOMAIN in self.hass.data and self.cluster_id in self.hass.data[DOMAIN]:
                trackers = self.hass.data[DOMAIN][self.cluster_id].get("trackers", {})
                if self.entity_id in trackers:
                    del trackers[self.entity_id]
                    _LOGGER.debug(
                        "Removed entity from internal storage: %s", self.entity_id
                    )
        except Exception as e:
            _LOGGER.error(
                "Failed to remove entity from internal storage: %s, Error: %s",
                self.entity_id,
                e,
            )

        _LOGGER.info("Entity successfully removed: %s", self.entity_id)


class DiveraAlarmTracker(BaseDiveraTracker):
    """A device tracker for alarms."""

    def __init__(self, coordinator, ucr_data, alarm_id, ucr_id):
        super().__init__(coordinator, ucr_data, ucr_id)
        self.alarm_id = alarm_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"device_tracker.{sanitize_entity_id(f'{self.ucr_id}_alarm_{self.alarm_id}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.ucr_id}_tracker_{self.alarm_id}"

    @property
    def name(self):
        """Return the name of the device tracker."""
        return f"Tracker Alarm ID {self.alarm_id}"

    @property
    def latitude(self):
        """Latitude of the tracker."""
        alarm_data = self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        alarm_data = self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("lng", 0)

    @property
    def icon(self):
        """Return an icon for the tracker."""
        alarm_data = self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})
        closed = alarm_data.get("closed", False)
        priority = alarm_data.get("priority", False)
        if closed:
            return I_CLOSED_ALARM
        elif priority:
            return I_OPEN_ALARM
        else:
            return I_OPEN_ALARM_NOPRIO


class DiveraVehicleTracker(BaseDiveraTracker):
    """A device tracker for vehicles."""

    def __init__(self, coordinator, ucr_data, vehicle_id: str, ucr_id: str):
        super().__init__(coordinator, ucr_data, ucr_id)
        self._vehicle_id = vehicle_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"device_tracker.{sanitize_entity_id(f'{self.ucr_id}_vehicle_{self._vehicle_id}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.ucr_id}_tracker_{self._vehicle_id}"

    @property
    def name(self):
        """Return the name of the device tracker."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name}"

    @property
    def latitude(self):
        """Latitude of the tracker."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        return vehicle_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        return vehicle_data.get("lng", 0)

    @property
    def gps_accuracy(self):
        # no standard value from divera
        return 100

    @gps_accuracy.setter
    def gps_accuracy(self, value):
        self._gps_accuracy = value

    @property
    def altitude(self):
        # no standard value from divera
        return 33

    @altitude.setter
    def altitude(self, value):
        self._altitude = value

    @property
    def course(self):
        # no standard value from divera
        return "Unknown"

    @course.setter
    def course(self, value):
        self._course = value

    @property
    def speed(self):
        # no standard value from divera
        return 0

    @speed.setter
    def speed(self, value):
        self._speed = value

    @property
    def vertical_accuracy(self):
        # no standard value from divera
        return 100

    @vertical_accuracy.setter
    def vertical_accuracy(self, value):
        self._vertical_accuracy = value

    @property
    def extra_state_attributes(self):
        """Return additional attributes, including icon color."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        status = str(
            vehicle_data.get("fmsstatus_id", "unknown")
        )  # Sicherstellen, dass es ein String ist

        color_map = {
            "1": "#55B300",  # Grün
            "2": "#198215",  # Dunkelgrün
            "3": "#FF460C",  # Orange-Rot
            "4": "#D60000",  # Rot
            "5": "#EFB200",  # Gelb
            "6": "#3E3E3E",  # Grau
            "7": "#0087E6",  # Blau
            "8": "#0038A9",  # Dunkelblau
            "9": "#001A7A",  # Navy
            "0": "#E400FF",  # Lila
        }

        return {
            "icon_color": color_map.get(status, "#808080"),  # Standard: Grau
        }

    @property
    def icon(self):
        """Return an icon for the tracker."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        status = vehicle_data.get("fmsstatus_id", "unknown")

        if status == "unknown":
            return "mdi:help-box"

        return f"mdi:numeric-{status}-box"
