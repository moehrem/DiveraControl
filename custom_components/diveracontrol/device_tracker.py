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
    D_VEHICLE,
    D_UCR,
    DOMAIN,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_VEHICLE,
    MANUFACTURER,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up Divera device trackers."""

    hub = config_entry.data
    hub_id = hub[D_UCR]
    coordinator = hass.data[DOMAIN][hub_id][D_COORDINATOR]
    current_trackers = hass.data[DOMAIN][hub_id].setdefault("trackers", {})

    async def sync_trackers():
        new_trackers = []
        active_alarms = coordinator.data.get(D_ALARM, {})
        active_vehicles = coordinator.data.get(D_VEHICLE, {})

        if isinstance(active_alarms, dict):
            active_alarms = set(active_alarms.keys())
        else:
            active_alarms = set()

        if isinstance(active_vehicles, dict):
            active_vehicles = set(active_vehicles.keys())
        else:
            active_vehicles = set()

        active_ids = active_alarms | active_vehicles

        # Add new alarm trackers
        new_alarm_trackers = active_alarms - current_trackers.keys()
        for alarm_id in new_alarm_trackers:
            tracker = DiveraAlarmTracker(coordinator, alarm_id, hub_id)
            new_trackers.append(tracker)
            current_trackers[alarm_id] = tracker

        # Add new vehicle trackers
        new_vehicle_trackers = active_vehicles - current_trackers.keys()
        for vehicle_id in new_vehicle_trackers:
            tracker = DiveraVehicleTracker(coordinator, vehicle_id, hub_id)
            new_trackers.append(tracker)
            current_trackers[vehicle_id] = tracker

        # Remove outdated trackers
        removed_trackers = set(current_trackers.keys()) - active_ids
        for tracker_id in removed_trackers:
            tracker = current_trackers.pop(tracker_id, None)
            if tracker:
                await tracker.remove_from_hass()
                _LOGGER.debug("Removed tracker: %s", tracker_id)

        # Add new trackers to Home Assistant
        if new_trackers:
            async_add_entities(new_trackers)

    # Initial synchronization
    await sync_trackers()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_trackers()))


class BaseDiveraTracker(TrackerEntity):
    """Base class for Divera device trackers."""

    def __init__(self, coordinator, hub_id):
        """Initialize the device tracker."""
        self.coordinator = coordinator
        # self.entity_id = entity_id
        self.hub_id = hub_id

    @property
    def device_info(self):
        """Return device information for the sensor."""
        self._name = "_".join(self.coordinator.data.get(D_CLUSTER_ADDRESS, {}).keys())
        return {
            "identifiers": {(DOMAIN, self._name)},
            "name": self._name,
            "manufacturer": MANUFACTURER,
            "model": DOMAIN,
            "sw_version": VERSION,
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
            if DOMAIN in self.hass.data and self.hub_id in self.hass.data[DOMAIN]:
                trackers = self.hass.data[DOMAIN][self.hub_id].get("trackers", {})
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

    def __init__(self, coordinator, alarm_id, hub_id):
        super().__init__(coordinator, hub_id)
        self.alarm_id = alarm_id

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"tracker_alarm_id_{self.alarm_id}"

    @property
    def name(self):
        """Return the name of the device tracker."""
        return f"Tracker Alarm ID {self.alarm_id}"

    @property
    def latitude(self):
        """Latitude of the tracker."""
        alarm_data = self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        alarm_data = self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("lng", 0)

    @property
    def icon(self):
        """Return an icon for the tracker."""
        alarm_data = self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})
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

    def __init__(self, coordinator, vehicle_id: str, hub_id: str):
        super().__init__(coordinator, hub_id)
        self._vehicle_id = vehicle_id

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"tracker_vehicle_{shortname}_{veh_name}"

    @property
    def entity_id(self):
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"device_tracker.{sanitize_entity_id(f"vehicle_{shortname}_{veh_name}")}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def name(self):
        """Return the name of the device tracker."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name}"

    @property
    def latitude(self):
        """Latitude of the tracker."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        return vehicle_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
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
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
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
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        status = vehicle_data.get("fmsstatus_id", "unknown")

        if status == "unknown":
            return "mdi:help-box"

        return f"mdi:numeric-{status}-box"
