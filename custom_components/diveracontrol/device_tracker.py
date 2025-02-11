"""Handles all device_tracker entities."""

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er

from .utils import BaseDiveraEntity, sanitize_entity_id, get_device_info
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
    PATCH_VERSION,
)

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up Divera device trackers."""

    cluster = config_entry.data
    cluster_id = cluster[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    async def sync_sensors():
        """Synchronize all trackers with the current data from coordinator."""

        new_trackers = []

        for ucr_id, ucr_data in coordinator.data.items():
            new_alarm_data = ucr_data.get(D_ALARM, {})
            new_vehicle_data = ucr_data.get(D_VEHICLE, {})

            if isinstance(new_alarm_data, dict):
                new_alarm_data = set(new_alarm_data.keys())
            else:
                new_alarm_data = set()

            if isinstance(new_vehicle_data, dict):
                new_vehicle_data = set(new_vehicle_data.keys())
            else:
                new_vehicle_data = set()

            test_current_trackers = (
                hass.data[DOMAIN][cluster_id]
                .setdefault(ucr_id, {})
                .setdefault("device_tracker", {})
            )

            # add alarm trackers
            new_alarm_tracker = new_alarm_data - test_current_trackers.keys()
            for alarm_id in new_alarm_tracker:
                tracker = DiveraAlarmTracker(coordinator, ucr_data, alarm_id, ucr_id)
                new_trackers.append(tracker)
                test_current_trackers[alarm_id] = tracker

            # add vehicle trackers
            new_vehicle_trackers = new_vehicle_data - test_current_trackers.keys()
            for vehicle_id in new_vehicle_trackers:
                tracker = DiveraVehicleTracker(
                    coordinator, ucr_data, vehicle_id, ucr_id
                )
                new_trackers.append(tracker)
                test_current_trackers[vehicle_id] = tracker

            # remove outdated sensors
            active_ids = new_alarm_data | new_vehicle_data
            removable_trackers = set(test_current_trackers.keys() - active_ids)
            for tracker_id in removable_trackers:
                sensor = test_current_trackers.pop(tracker_id, None)
                if sensor:
                    await sensor.remove_from_hass()
                    LOGGER.debug("Removed trackers: %s", tracker_id)

        # Add new trackers to Home Assistant
        if new_trackers:
            async_add_entities(new_trackers, update_before_add=True)

    await sync_sensors()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


# class BaseDiveraTracker(TrackerEntity):
#     """Baseclass for Divera-Tracker."""

#     def __init__(self, coordinator, ucr_data, ucr_id: str) -> None:
#         """Init class BaseDiveraTracker."""
#         self.coordinator = coordinator
#         self.cluster_id = coordinator.cluster_id
#         self.ucr_id = ucr_id
#         self.ucr_data = ucr_data

#     @property
#     def device_info(self):
#         """Return device information for the tracker."""
#         self.firstname = self.ucr_data.get(D_USER, {}).get("firstname", "")
#         self.lastname = self.ucr_data.get(D_USER, {}).get("lastname", "")
#         return {
#             "identifiers": {(DOMAIN, f"{self.firstname} {self.lastname}")},
#             "name": f"{self.firstname} {self.lastname} / {self.ucr_id}",
#             "manufacturer": MANUFACTURER,
#             "model": DOMAIN,
#             "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
#             "entry_type": "service",
#         }

#     @property
#     def should_poll(self):
#         """Indicate that the entity does not require polling."""
#         return False

#     async def async_added_to_hass(self) -> None:
#         """Register updates."""
#         self.async_on_remove(
#             self.coordinator.async_add_listener(self.async_write_ha_state)
#         )

#     # async def async_update(self) -> None:
#     #     """Fordere ein Update vom Koordinator an."""
#     #     await self.coordinator.async_request_refresh()

#     async def remove_from_hass(self) -> None:
#         """Vollständige Entfernung der Entität aus Home Assistant."""
#         LOGGER.debug("Starting removal process for entity: %s", self.entity_id)

#         # 1. Entferne die Entität aus dem Entity Registry
#         try:
#             registry = er.async_get(self.hass)
#             if registry.async_is_registered(self.entity_id):
#                 registry.async_remove(self.entity_id)
#                 LOGGER.debug("Removed entity from registry: %s", self.entity_id)
#             else:
#                 LOGGER.debug("Entity not found in registry: %s", self.entity_id)
#         except Exception as e:
#             LOGGER.error(
#                 "Failed to remove entity from registry: %s, Error: %s",
#                 self.entity_id,
#                 e,
#             )

#         # 2. Entferne die Entität aus dem State Machine
#         try:
#             self.hass.states.async_remove(self.entity_id)
#             LOGGER.debug("Removed entity from state machine: %s", self.entity_id)
#         except Exception as e:
#             LOGGER.error(
#                 "Failed to remove entity from state machine: %s, Error: %s",
#                 self.entity_id,
#                 e,
#             )

#         # 3. Entferne die Entität aus internen Datenstrukturen
#         try:
#             if DOMAIN in self.hass.data and self.cluster_id in self.hass.data[DOMAIN]:
#                 trackers = self.hass.data[DOMAIN][self.cluster_id].get("trackers", {})
#                 if self.entity_id in trackers:
#                     del trackers[self.entity_id]
#                     LOGGER.debug(
#                         "Removed entity from internal storage: %s", self.entity_id
#                     )
#         except Exception as e:
#             LOGGER.error(
#                 "Failed to remove entity from internal storage: %s, Error: %s",
#                 self.entity_id,
#                 e,
#             )

#         LOGGER.info("Entity successfully removed: %s", self.entity_id)


class BaseDiveraTracker(TrackerEntity, BaseDiveraEntity):
    """Basisklasse für Divera-Tracker."""

    def __init__(self, coordinator, ucr_data, ucr_id: str) -> None:
        """Initialisiert einen Tracker."""
        TrackerEntity.__init__(self)
        BaseDiveraEntity.__init__(self, coordinator, ucr_data, ucr_id)

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.ucr_data, self.ucr_id)


class DiveraAlarmTracker(BaseDiveraTracker):
    """A device tracker for alarms."""

    def __init__(self, coordinator, ucr_data, alarm_id, ucr_id):
        super().__init__(coordinator, ucr_data, ucr_id)
        self.alarm_id = alarm_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"device_tracker.{sanitize_entity_id(f'{self.ucr_id}_alarmtracker_{self.alarm_id}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.ucr_id}_alarmtracker_{self.alarm_id}"

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
        return f"device_tracker.{sanitize_entity_id(f'{self.ucr_id}_vehicletracker_{self._vehicle_id}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.ucr_id}_vehicletracker_{self._vehicle_id}"

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
