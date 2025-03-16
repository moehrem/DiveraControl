"""Handles all device_tracker entities."""

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.components.device_tracker.config_entry import TrackerEntity
import homeassistant.helpers.entity_registry as er

from .utils import BaseDiveraEntity, get_device_info
from .const import (
    D_ALARM,
    D_COORDINATOR,
    D_CLUSTER_ID,
    D_CLUSTER,
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

    async def sync_trackers():
        """Synchronize all trackers with the current data from coordinator."""

        cluster_data = coordinator.cluster_data
        current_trackers = hass.data[DOMAIN][cluster_id].setdefault(
            "device_tracker", {}
        )
        new_trackers = []

        new_alarm_data = cluster_data.get(D_ALARM, {}).get("items", {})
        new_vehicle_data = cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})

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

        #####
        # register new tracker
        if new_trackers:
            async_add_entities(new_trackers, update_before_add=True)

        #####
        # update existing trackers
        for tracker in current_trackers.values():
            if isinstance(tracker, BaseDiveraTracker):
                new_data = get_new_tracker_data(tracker)
                if new_data:
                    asyncio.create_task(tracker.async_update_state(new_data))

        #####
        # remove outdated trackers
        active_ids = new_alarm_data | new_vehicle_data
        removable_trackers = set(current_trackers.keys() - active_ids)
        for tracker_id in removable_trackers:
            sensor = current_trackers.pop(tracker_id, None)
            if sensor:
                await sensor.remove_from_hass()
                LOGGER.debug("Removed trackers: %s", tracker_id)

    await sync_trackers()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_trackers()))


def get_new_tracker_data(sensor) -> dict[str, Any]:
    """Gibt die aktuellen Daten für den Tracker aus coordinator.data zurück."""
    if isinstance(sensor, DiveraAlarmTracker):
        return (
            sensor.coordinator.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(sensor.alarm_id, {})
        )

    if isinstance(sensor, DiveraVehicleTracker):
        return (
            sensor.coordinator.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(sensor._vehicle_id, {})
        )

    return {}


class BaseDiveraTracker(TrackerEntity, BaseDiveraEntity):
    """Basisklasse für Divera-Tracker."""

    def __init__(self, coordinator, cluster_data, cluster_id: str) -> None:
        """Initialisiert einen Tracker."""
        TrackerEntity.__init__(self)
        BaseDiveraEntity.__init__(self, coordinator, cluster_data, cluster_id)

        self.ucr_id = cluster_data.get(D_UCR_ID, "")
        self.cluster_name = cluster_data.get(D_CLUSTER, {}).get("name", "No name found")

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
        self._alarm_data = (
            self.cluster_data.get(D_ALARM, {}).get("items", {}).get(self.alarm_id, {})
        )

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
        return self._alarm_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        return self._alarm_data.get("lng", 0)

    @property
    def icon(self):
        """Return an icon for the tracker."""
        closed = self._alarm_data.get("closed", False)
        priority = self._alarm_data.get("priority", False)
        if closed:
            return I_CLOSED_ALARM
        elif priority:
            return I_OPEN_ALARM
        else:
            return I_OPEN_ALARM_NOPRIO

    async def async_update_state(self, new_data: dict[str, Any]) -> None:
        """Aktualisiert den Zustand des Trackers, wenn sich die Alarmdaten geändert haben."""
        updated = False

        # Korrektes Mapping der Schlüssel für Koordinaten
        key_mapping = {"lat": "latitude", "lng": "longitude"}

        # Kopiere die Daten, um Änderungen während der Iteration zu vermeiden
        new_data_copy = dict(new_data)

        # Iteriere über die Kopie der neuen Daten und aktualisiere die internen Werte
        for key, value in new_data_copy.items():
            mapped_key = key_mapping.get(
                key, key
            )  # Mapping anwenden, falls erforderlich

            if self._alarm_data.get(mapped_key) != value:
                self._alarm_data[mapped_key] = value
                self.coordinator.cluster_data[D_ALARM]["items"][self.alarm_id][
                    mapped_key
                ] = value
                updated = True

        # Falls sich etwas geändert hat, die UI in Home Assistant aktualisieren
        if updated:
            self.async_write_ha_state()


class DiveraVehicleTracker(BaseDiveraTracker):
    """A device tracker for vehicles."""

    def __init__(self, coordinator, cluster_data, vehicle_id: str, cluster_id: str):
        super().__init__(coordinator, cluster_data, cluster_id)
        self._vehicle_id = vehicle_id
        self._vehicle_data = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self._vehicle_id, {})
        )

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
        shortname = self._vehicle_data.get("shortname", "Unknown")
        veh_name = self._vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name}"

    @property
    def latitude(self):
        """Latitude of the tracker."""

        return self._vehicle_data.get("lat", 0)

    @property
    def longitude(self):
        """Longitude of the tracker."""
        return self._vehicle_data.get("lng", 0)

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
        status = self._vehicle_data.get("fmsstatus_id", "unknown")

        if status == "unknown":
            return "mdi:help-box"

        return f"mdi:numeric-{status}-box"

    async def async_update_state(self, new_data: dict) -> None:
        """Aktualisiert den Zustand des Trackers, wenn sich Fahrzeugdaten geändert haben."""
        updated = False

        # Kopiere die Daten, um Änderungen während der Iteration zu vermeiden
        new_data_copy = dict(new_data)

        # Key-Mapping für Koordinaten
        key_mapping = {"lat": "latitude", "lng": "longitude"}

        for key, value in new_data_copy.items():
            mapped_key = key_mapping.get(key, key)  # Falls lat/lng, dann umwandeln

            if self._vehicle_data.get(mapped_key) != value:
                self._vehicle_data[mapped_key] = value
                self.coordinator.cluster_data[D_CLUSTER][D_VEHICLE][self._vehicle_id][
                    mapped_key
                ] = value
                updated = True

        if updated:
            self.async_write_ha_state()
