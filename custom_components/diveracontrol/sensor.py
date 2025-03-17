"""Definition of Home Assistant Sensors for the Divera Integration.

Responsibilities:
- Subscribe to data from the DataUpdateCoordinator (per HUB).
- Provide sensor data (state, extra_state_attributes, etc.) for Home Assistant.
- Handle attributes such as unique_id, name, etc., required for sensor integration.
- Adding and removing of sensors.

Communication:
- Retrieves data from the DataUpdateCoordinator (per HUB).
- Delivers data to Home Assistant for display in the user interface or use in automations.


"""

import asyncio
import logging
from typing import Set, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.entity_registry as er

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
from .utils import BaseDiveraEntity, get_device_info

LOGGER = logging.getLogger(__name__)


# async def async_setup_entry(
#     hass: HomeAssistant, config_entry, async_add_entities
# ) -> None:
#     """Set up the Divera sensors."""

#     cluster = config_entry.data
#     cluster_id = cluster[D_CLUSTER_ID]
#     coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

#     async def sync_sensors():
#         """Synchronize all sensors with the current data from coordinator."""

#         cluster_data = coordinator.cluster_data
#         current_sensors = hass.data[DOMAIN][cluster_id].setdefault("sensors", {})
#         new_sensors = []

#         new_alarm_data = cluster_data.get(D_ALARM, {}).get("items")
#         new_vehicle_data = cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
#         new_status_data = cluster_data.get(D_CLUSTER, {}).get(D_STATUS, {})
#         new_static_sensors_data = {
#             D_OPEN_ALARMS,
#             D_CLUSTER,
#         }

#         if isinstance(new_alarm_data, dict):
#             new_alarm_data = set(new_alarm_data.keys())
#         else:
#             new_alarm_data = set()

#         if isinstance(new_vehicle_data, dict):
#             new_vehicle_data = set(new_vehicle_data.keys())
#         else:
#             new_vehicle_data = set()

#         if isinstance(new_status_data, dict):
#             new_status_data = set(new_status_data.keys())
#         else:
#             new_status_data = set()

#         # adding alarm sensors
#         new_alarms = new_alarm_data - current_sensors.keys()
#         for alarm_id in new_alarms:
#             sensor = DiveraAlarmSensor(coordinator, cluster_data, alarm_id, cluster_id)
#             new_sensors.append(sensor)
#             current_sensors[alarm_id] = sensor

#         # adding vehicle sensors
#         new_vehicles = new_vehicle_data - current_sensors.keys()
#         for vehicle_id in new_vehicles:
#             sensor = DiveraVehicleSensor(
#                 coordinator, cluster_data, vehicle_id, cluster_id
#             )
#             new_sensors.append(sensor)
#             current_sensors[vehicle_id] = sensor

#         # adding availabiity sensor
#         new_status = new_status_data - current_sensors.keys()
#         for status_id in new_status:
#             sensor = DiveraAvailabilitySensor(
#                 coordinator, cluster_data, cluster_id, status_id
#             )
#             new_sensors.append(sensor)
#             current_sensors[status_id] = sensor

#         # adding static sensors
#         static_sensor_map = {
#             D_OPEN_ALARMS: DiveraOpenAlarmsSensor(
#                 coordinator, cluster_data, cluster_id
#             ),
#             D_CLUSTER: DiveraUnitSensor(coordinator, cluster_data, cluster_id),
#         }

#         for sensor_name, sensor_instance in static_sensor_map.items():
#             if sensor_name not in current_sensors:
#                 new_sensors.append(sensor_instance)
#                 current_sensors[sensor_name] = sensor_instance

#         #####
#         # register new sensors
#         if new_sensors:
#             async_add_entities(new_sensors, update_before_add=True)

#         #####
#         # updating existing sensors
#         for sensor in current_sensors.values():
#             if isinstance(sensor, BaseDiveraSensor):
#                 new_data = get_new_sensor_data(sensor)
#                 if new_data:
#                     asyncio.create_task(sensor.async_update_state(new_data))

#         #####
#         # remove outdated sensors
#         active_ids = (
#             new_alarm_data
#             | new_vehicle_data
#             | new_static_sensors_data
#             | new_status_data
#         )
#         removable_sensors = set(current_sensors.keys() - active_ids)
#         for sensor_id in removable_sensors:
#             sensor = current_sensors.pop(sensor_id, None)
#             if sensor:
#                 await sensor.remove_from_hass()
#                 LOGGER.debug("Removed sensor: %s", sensor_id)

#     await sync_sensors()

#     # adding listener for updates
#     coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up the Divera sensors."""

    cluster_id = config_entry.data[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]
    current_sensors = hass.data[DOMAIN][cluster_id].setdefault("sensors", {})

    async def async_add_sensor():
        """Fügt neue Sensoren hinzu."""
        cluster_data = coordinator.cluster_data
        new_sensors = []

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
        new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
        new_status_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_STATUS))
        new_static_sensors_data = {D_OPEN_ALARMS, D_CLUSTER}

        # Alarm-Sensoren hinzufügen
        for alarm_id in new_alarm_data - current_sensors.keys():
            sensor = DiveraAlarmSensor(coordinator, alarm_id, cluster_id)
            new_sensors.append(sensor)
            current_sensors[alarm_id] = sensor

        # Fahrzeug-Sensoren hinzufügen
        for vehicle_id in new_vehicle_data - current_sensors.keys():
            sensor = DiveraVehicleSensor(coordinator, vehicle_id, cluster_id)
            new_sensors.append(sensor)
            current_sensors[vehicle_id] = sensor

        # Status-Sensoren hinzufügen
        for status_id in new_status_data - current_sensors.keys():
            sensor = DiveraAvailabilitySensor(coordinator, cluster_id, status_id)
            new_sensors.append(sensor)
            current_sensors[status_id] = sensor

        # Statische Sensoren hinzufügen
        static_sensor_map = {
            D_OPEN_ALARMS: DiveraOpenAlarmsSensor(coordinator, cluster_id),
            D_CLUSTER: DiveraUnitSensor(coordinator, cluster_id),
        }

        for sensor_name, sensor_instance in static_sensor_map.items():
            if sensor_name not in current_sensors:
                new_sensors.append(sensor_instance)
                current_sensors[sensor_name] = sensor_instance

        # Sensoren zur HA-Plattform hinzufügen
        if new_sensors:
            async_add_entities(new_sensors, update_before_add=True)

    async def async_update_sensor():
        """Aktualisiert bestehende Sensoren."""
        update_tasks = []
        for sensor_data in current_sensors.values():
            if isinstance(sensor_data, BaseDiveraSensor):
                new_data = get_new_sensor_data(sensor_data)
                if new_data:
                    update_tasks.append(sensor_data.async_update_state(new_data))

        if update_tasks:
            await asyncio.gather(*update_tasks)

    async def async_remove_sensor():
        """Entfernt Sensoren, die nicht mehr benötigt werden."""
        cluster_data = coordinator.cluster_data

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
        new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
        new_status_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_STATUS))
        new_static_sensors_data = {D_OPEN_ALARMS, D_CLUSTER}

        active_ids = (
            new_alarm_data
            | new_vehicle_data
            | new_status_data
            | new_static_sensors_data
        )
        removable_sensors = set(current_sensors.keys()) - active_ids

        remove_tasks = []
        for sensor_id in removable_sensors:
            sensor = current_sensors.pop(sensor_id, None)
            if sensor:
                remove_tasks.append(sensor.remove_from_hass())
                LOGGER.debug("Removed sensor: %s", sensor_id)

        if remove_tasks:
            await asyncio.gather(*remove_tasks)

    # Initialer Aufruf für Sensor-Setup
    await async_add_sensor()
    await async_update_sensor()
    await async_remove_sensor()

    # Listener für automatische Updates registrieren
    coordinator.async_add_listener(lambda: asyncio.create_task(async_add_sensor()))
    coordinator.async_add_listener(lambda: asyncio.create_task(async_update_sensor()))
    coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_sensor()))


def extract_keys(data) -> Set[str]:
    """Extrahiert Schlüsselwerte aus Dictionaries."""
    return set(data.keys()) if isinstance(data, dict) else set()


async def async_remove_sensors(hass: HomeAssistant, cluster_id: str) -> None:
    """Remove all sensors for a specific HUB."""
    if DOMAIN in hass.data and cluster_id in hass.data[DOMAIN]:
        sensors = hass.data[DOMAIN][cluster_id].get("sensors", {})
        for sensor_id, sensor in sensors.items():
            sensor.remove_from_hass()
            LOGGER.info("Removed sensor: %s for HUB: %s", sensor_id, cluster_id)

        # remove sensor list
        hass.data[DOMAIN][cluster_id].pop("sensors", None)


def get_new_sensor_data(sensor) -> dict[str, Any]:
    """Gibt die aktuellen Daten für den Sensor aus coordinator.data zurück."""
    if isinstance(sensor, DiveraAlarmSensor):
        return (
            sensor.coordinator.cluster_data.get(D_ALARM, {})
            .get("items", {})
            .get(sensor.alarm_id, {})
        )

    if isinstance(sensor, DiveraVehicleSensor):
        return (
            sensor.coordinator.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(sensor._vehicle_id, {})
        )

    if isinstance(sensor, DiveraAvailabilitySensor):
        return (
            sensor.coordinator.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(sensor.status_id, {})
        )

    return {}


class BaseDiveraSensor(Entity, BaseDiveraEntity):
    """Basisklasse für Divera-Sensoren."""

    def __init__(self, coordinator, cluster_id: str) -> None:
        """Initialisiert einen Sensor."""
        Entity.__init__(self)
        BaseDiveraEntity.__init__(self, coordinator, cluster_id)

        # self.cluster_id = coordinator.cluster_id
        self.cluster_name = coordinator.cluster_name

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.cluster_name)


class DiveraAlarmSensor(BaseDiveraSensor):
    """Sensor to represent a single alarm."""

    def __init__(self, coordinator, alarm_id: str, cluster_id: str) -> None:
        """Init class DiveraAlarmSensor."""
        super().__init__(coordinator, cluster_id)
        self.alarm_id = alarm_id
        self.alarm_data = (
            self.cluster_data.get(D_ALARM, {}).get("items", {}).get(self.alarm_id, {})
        )

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_alarm_{self.alarm_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

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
        # alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return self.alarm_data.get("title", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        return self.alarm_data

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        # alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
        closed = self.alarm_data.get("closed", False)
        priority = self.alarm_data.get("priority", False)
        if closed:
            return I_CLOSED_ALARM
        if priority:
            return I_OPEN_ALARM

        return I_OPEN_ALARM_NOPRIO

    async def async_update_state(self, new_data: dict[str, Any]):
        """Wird aufgerufen, wenn sich der Zustand des Sensors ändert."""
        updated = False
        for key, value in new_data.items():
            if self.alarm_data.get(key) != value:
                self.alarm_data[key] = value
                updated = True

        if updated:
            self.async_write_ha_state()
            LOGGER.info("Updated sensor: %s", self.alarm_id)


class DiveraVehicleSensor(BaseDiveraSensor):
    """Sensor to represent a single vehicle."""

    def __init__(self, coordinator, vehicle_id: str, cluster_id: str) -> None:
        """Init class DiveraVehicleSensor."""
        super().__init__(coordinator, cluster_id)
        self._vehicle_id = vehicle_id
        self._vehicle_data = (
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self._vehicle_id, {})
        )

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_vehicle_{self._vehicle_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique if if sensor."""
        return f"{self.cluster_id}_vehicle_{self._vehicle_id}"

    @property
    def name(self) -> str:
        """Name of sensor."""
        shortname = self._vehicle_data.get("shortname", "Unknown")
        veh_name = self._vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name}"

    @property
    def state(self) -> str:
        """State of sensor."""
        return self._vehicle_data.get("fmsstatus_id", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        extra_state_attributes = {}
        extra_state_attributes["vehicle_id"] = self._vehicle_id
        extra_state_attributes.update(
            self.cluster_data.get(D_CLUSTER, {})
            .get(D_VEHICLE, {})
            .get(self._vehicle_id, {})
        )
        return extra_state_attributes

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_VEHICLE

    async def async_update_state(self, new_data: dict[str, Any]):
        """Aktualisiert den Sensor-Zustand, wenn sich Daten geändert haben."""
        updated = False
        for key, value in new_data.items():
            if key == "status":
                key = "fmsstatus_id"

            if self._vehicle_data.get(key) != value:
                self._vehicle_data[key] = value
                updated = True

        if updated:
            self.async_write_ha_state()
            LOGGER.info(
                "Updated sensor: %s",
                f"{self._vehicle_data.get('shortname', 'Unknown')} / {self._vehicle_data.get('name', 'Unknown')}",
            )


class DiveraUnitSensor(BaseDiveraSensor):
    """Sensor to represent a divera-unit."""

    def __init__(self, coordinator, cluster_id: str) -> None:
        """Init class DiveraUnitSensor."""
        super().__init__(coordinator, cluster_id)

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_cluster_address'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

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
        cluster_address = self.cluster_data.get(D_CLUSTER, {}).get("address", "Unknown")
        return {
            "cluster_id": self.cluster_id,
            "shortname": cluster_shortname,
            "latitude": cluster_address.get("lat"),
            "longitude": cluster_address.get("lng"),
            "street": cluster_address.get("street"),
            "zip": cluster_address.get("zip"),
            "city": cluster_address.get("city"),
            "country": cluster_address.get("country"),
            "ags": cluster_address.get("ags"),
        }

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_FIRESTATION

    async def async_update_state(self, new_data: dict[str, Any]):
        """Aktualisiert den Sensor-Zustand, wenn sich Daten geändert haben."""
        updated = False

        # Aktualisieren des cluster_shortname
        cluster_shortname = new_data.get("shortname", "Unknown")
        if self.cluster_data.get(D_CLUSTER, {}).get("shortname") != cluster_shortname:
            self.cluster_data[D_CLUSTER]["shortname"] = cluster_shortname
            updated = True

        # Aktualisieren der Adresse
        cluster_address = new_data.get("address", {})
        current_address = self.cluster_data.get(D_CLUSTER, {}).get("address", {})

        for key in ["lat", "lng", "street", "zip", "city", "country", "ags"]:
            if cluster_address.get(key) != current_address.get(key):
                self.cluster_data[D_CLUSTER]["address"][key] = cluster_address.get(key)
                updated = True

        # Falls sich etwas geändert hat, UI-Update in Home Assistant auslösen
        if updated:
            self.async_write_ha_state()
            LOGGER.info("Updated sensor: %s", self.cluster_name)


class DiveraOpenAlarmsSensor(BaseDiveraSensor):
    """Sensor to count active alarms."""

    def __init__(self, coordinator, cluster_id: str) -> None:
        """Init class DiveraOpenAlarmsSensor."""
        super().__init__(coordinator, cluster_id)

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_open_alarms'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"{self.cluster_id}_open_alarms"

    @property
    def name(self) -> str:
        """Name of sensor."""
        # return f"Open Alarms {self.cluster_id}"
        return "Open Alarms"

    @property
    def state(self) -> int:
        """State of sensor."""
        return self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_COUNTER_ACTIVE_ALARMS

    async def async_update_state(self, new_data: dict[str, Any]):
        """Aktualisiert den Sensor-Zustand, wenn sich die Anzahl offener Alarme geändert hat."""
        updated = False

        # Extrahiere die neue Anzahl offener Alarme aus new_data
        new_open_alarms = new_data.get(D_OPEN_ALARMS, 0)

        # Prüfe, ob sich der Wert geändert hat
        if self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0) != new_open_alarms:
            self.cluster_data[D_ALARM][D_OPEN_ALARMS] = new_open_alarms
            updated = True

        # Falls sich der Wert geändert hat, die UI in Home Assistant aktualisieren
        if updated:
            self.async_write_ha_state()
            LOGGER.info("Updated sensor: %s", "Open Alarms")


class DiveraAvailabilitySensor(BaseDiveraSensor):
    """Sensor to return personal status."""

    def __init__(self, coordinator: dict, cluster_id: str, status_id: str) -> None:
        """Init class DiveraAvailabilitySensor."""
        super().__init__(coordinator, cluster_id)
        self.status_id = status_id

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_status_{self.status_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_status_{self.status_id}'}"

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

    async def async_update_state(self, new_data: dict[str, Any]):
        """Aktualisiert den Sensor-Zustand, wenn sich die Verfügbarkeitsdaten geändert haben."""
        updated = False

        # Extrahiere den neuen Verfügbarkeitswert
        new_state = new_data.get("all", 0)
        current_state = (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("all", 0)
        )

        if new_state != current_state:
            self.cluster_data[D_MONITOR]["1"][self.status_id]["all"] = new_state
            updated = True

        # Aktualisieren der zusätzlichen Attribute
        new_qualification_data = new_data.get("qualification", {})
        current_qualification_data = (
            self.cluster_data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("qualification", {})
        )

        if new_qualification_data != current_qualification_data:
            self.cluster_data[D_MONITOR]["1"][self.status_id]["qualification"] = (
                new_qualification_data
            )
            updated = True

        # Falls sich Daten geändert haben, die UI in Home Assistant aktualisieren
        if updated:
            self.async_write_ha_state()
            status_name = (
                self.cluster_data.get(D_CLUSTER, {})
                .get(D_STATUS, {})
                .get(self.status_id, {})
                .get("name", "Unknown")
            )
            LOGGER.info("Updated sensor: %s", f"Verfügbarkeit: {status_name}")
