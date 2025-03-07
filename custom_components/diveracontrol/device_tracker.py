"""Handles all device_tracker entities."""

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er

from .utils import BaseDiveraEntity, get_device_info
from .const import (
    D_ALARM,
    D_COORDINATOR,
    D_CLUSTER_ADDRESS,
    D_CLUSTER_ID,
    D_VEHICLE,
    D_UCR,
    D_UCR_ID,
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

        cluster_data = coordinator.cluster_data
        current_trackers = hass.data[DOMAIN][cluster_id].setdefault(
            "device_tracker", {}
        )
        new_trackers = []

        new_alarm_data = cluster_data.get(D_ALARM, {})
        new_vehicle_data = cluster_data.get(D_VEHICLE, {})

        if isinstance(new_alarm_data, dict):
            new_alarm_data = set(new_alarm_data.keys())
        else:
            new_alarm_data = set()

        if isinstance(new_vehicle_data, dict):
            new_vehicle_data = set(new_vehicle_data.keys())
        else:
            new_vehicle_data = set()

        # add alarm trackers
        new_alarm_tracker = new_alarm_data - current_trackers.keys()
        for alarm_id in new_alarm_tracker:
            tracker = DiveraAlarmTracker(
                coordinator, cluster_data, alarm_id, cluster_id
            )
            new_trackers.append(tracker)
            current_trackers[alarm_id] = tracker

        # add vehicle trackers
        new_vehicle_trackers = new_vehicle_data - current_trackers.keys()
        for vehicle_id in new_vehicle_trackers:
            tracker = DiveraVehicleTracker(
                coordinator, cluster_data, vehicle_id, cluster_id
            )
            new_trackers.append(tracker)
            current_trackers[vehicle_id] = tracker

        # remove outdated sensors
        active_ids = new_alarm_data | new_vehicle_data
        removable_trackers = set(current_trackers.keys() - active_ids)
        for tracker_id in removable_trackers:
            sensor = current_trackers.pop(tracker_id, None)
            if sensor:
                await sensor.remove_from_hass()
                LOGGER.debug("Removed trackers: %s", tracker_id)

        # Add new trackers to Home Assistant
        if new_trackers:
            async_add_entities(new_trackers, update_before_add=True)

    await sync_sensors()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


class BaseDiveraTracker(TrackerEntity, BaseDiveraEntity):
    """Basisklasse für Divera-Tracker."""

    def __init__(self, coordinator, cluster_data, cluster_id: str) -> None:
        """Initialisiert einen Tracker."""
        TrackerEntity.__init__(self)
        BaseDiveraEntity.__init__(self, coordinator, cluster_data, cluster_id)

        self.ucr_id = cluster_data.get(D_UCR_ID, "")
        self.cluster_name = (
            cluster_data.get(D_UCR, {}).get(self.ucr_id, {}).get("name", "Unit Unknown")
        )

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.cluster_name)


class DiveraAlarmTracker(BaseDiveraTracker):
    """A device tracker for alarms."""

    def __init__(self, coordinator, cluster_data, alarm_id, cluster_id) -> None:
        """Initialize an alarm tracker."""
        super().__init__(coordinator, cluster_data, cluster_id)
        self.alarm_id = alarm_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"device_tracker.{f'{self.cluster_id}_alarmtracker_{self.alarm_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

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
        alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("lng", 0)

    @property
    def icon(self):
        """Return an icon for the tracker."""
        alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
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

    def __init__(self, coordinator, cluster_data, vehicle_id: str, cluster_id: str):
        super().__init__(coordinator, cluster_data, cluster_id)
        self._vehicle_id = vehicle_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return (
            f"device_tracker.{f'{self.cluster_id}_vehicletracker_{self._vehicle_id}'}"
        )

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self):
        """Return a unique ID for this tracker."""
        return f"{self.cluster_id}_vehicletracker_{self._vehicle_id}"

    @property
    def name(self):
        """Return the name of the device tracker."""
        vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name}"

    @property
    def latitude(self):
        """Latitude of the tracker."""
        vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        return vehicle_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
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
        vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        status = vehicle_data.get("fmsstatus_id", "unknown")

        if status == "unknown":
            return "mdi:help-box"

        return f"mdi:numeric-{status}-box"
