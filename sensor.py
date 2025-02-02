"""Definition der Home Assistant Sensoren für die Divera-Integration.

Verantwortung:
    - Abonnieren der Daten vom DataUpdateCoordinator (pro HUB).
    - Bereitstellen von Sensordaten (state, extra_state_attributes, etc.) für Home Assistant.
    - Handhaben von Attributen wie unique_id, name, etc., die für die Sensorintegration benötigt werden.

Kommunikation:
    - Bezieht die Daten vom DataUpdateCoordinator (pro HUB).
    - Liefert die Daten an Home Assistant zur Anzeige in der Benutzeroberfläche oder zur Nutzung in Automationen.
"""

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.entity_registry as er

from .const import (
    D_ACTIVE_ALARM_COUNT,
    D_ALARM,
    # D_ALARMS,
    # D_VEHICLE_STATUS,
    D_CLUSTER_ADDRESS,
    D_COORDINATOR,
    D_DATA,
    D_CLUSTER_ID,
    # new structure
    D_STATUS,
    D_STATUS_CONF,
    D_UCR,
    D_VEHICLE,
    D_USER,
    DOMAIN,
    I_CLOSED_ALARM,
    I_COUNTER_ACTIVE_ALARMS,
    I_FIRESTATION,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_STATUS,
    I_VEHICLE,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
)
from .utils import sanitize_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up the Divera sensors."""

    cluster = config_entry.data
    cluster_id = cluster[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]
    # current_sensors = hass.data[DOMAIN][cluster_id].setdefault("sensors", {})
    usergroup_id = (
        coordinator.data.get(D_UCR, {}).get(cluster_id, {}).get("usergroup_id", None)
    )

    async def sync_sensors():
        """Synchronize all sensors with the current data from coordinator."""

        new_sensors = []

        for ucr_id, ucr_data in coordinator.data.items():
            ucr_alarm_data = ucr_data.get(D_ALARM, {})
            ucr_vehicle_data = ucr_data.get(D_VEHICLE, {})
            ucr_static_sensors_data = {
                D_ACTIVE_ALARM_COUNT: ucr_data.get(D_ACTIVE_ALARM_COUNT, ""),
                D_CLUSTER_ADDRESS: ucr_data.get(D_CLUSTER_ADDRESS, {}),  # OK
                D_STATUS: ucr_data.get(D_STATUS, {}),  # OK
            }

            entity_registry = er.async_get(hass)

            # Hole alle registrierten Sensoren für die `ucr_id`
            current_sensors = {
                entity.entity_id: entity
                for entity in entity_registry.entities.values()
                if entity.platform == DOMAIN
                and entity.domain == "sensor"
                and entity.unique_id.startswith(f"{ucr_id}_")
            }
            active_alarms = {
                sensor_id
                for sensor_id in current_sensors
                if f"sensor.{ucr_id}_alarm_" in sensor_id
            }

            active_vehicles = {
                vehicle_id
                for vehicle_id in current_sensors
                if f"sensor.{ucr_id}_vehicle_" in vehicle_id
            }

            active_static_sensors = {
                static_sensor_id
                for static_sensor_id in current_sensors
                if static_sensor_id not in active_alarms
                and static_sensor_id not in active_vehicles
            }

            # Add or update status sensors
            static_sensor_map = {
                D_ACTIVE_ALARM_COUNT: DiveraAlarmCountSensor(
                    coordinator, ucr_data, ucr_id
                ),
                D_CLUSTER_ADDRESS: DiveraFirestationSensor(
                    coordinator, ucr_data, ucr_id
                ),
            }

            # adding status sensor only for personal user, not monitor- or system-user
            if usergroup_id in [5, 19]:
                _LOGGER.debug("No personal account, will not create status sensor")
            else:
                static_sensor_map[D_STATUS] = DiveraStatusSensor(
                    coordinator, ucr_data, ucr_id
                )

            active_static_sensor_ids = {
                sensor_id.split("_", 1)[1] for sensor_id in active_static_sensors
            }

            for sensor_name, sensor_instance in static_sensor_map.items():
                if sensor_name not in active_static_sensor_ids:
                    _LOGGER.debug("Adding static sensor: %s", sensor_name)
                    new_sensors.append(sensor_instance)
                    # current_sensors[sensor_name] = sensor_instance

            # Add new alarm sensors
            active_alarm_ids = {sensor_id.split("_")[-1] for sensor_id in active_alarms}
            new_alarms = {
                alarm_id
                for alarm_id in ucr_alarm_data
                if alarm_id not in active_alarm_ids
            }

            for alarm_id in new_alarms:
                sensor = DiveraAlarmSensor(coordinator, ucr_data, alarm_id, ucr_id)
                _LOGGER.debug("Adding alarm sensor: %s", alarm_id)
                new_sensors.append(sensor)
                # current_sensors[alarm_id] = sensor

            # Add new vehicle sensors
            active_vehicle_ids = {
                vehicle_id.split("_")[-1] for vehicle_id in active_vehicles
            }
            new_vehicles = {
                vehicle_id
                for vehicle_id in ucr_vehicle_data
                if vehicle_id not in active_vehicle_ids
            }
            for vehicle_id in new_vehicles:
                sensor = DiveraVehicleSensor(coordinator, ucr_data, vehicle_id, ucr_id)
                _LOGGER.debug("Adding vehicle sensor: %s", vehicle_id)
                new_sensors.append(sensor)
                # current_sensors[vehicle_id] = sensor

            # remove outdated sensors
            active_sensor_ids = (
                active_alarm_ids | active_vehicle_ids | active_static_sensor_ids
            )

            old_sensors = {
                sensor_id
                for sensor_id in active_sensor_ids
                if sensor_id not in ucr_alarm_data
                and sensor_id not in ucr_vehicle_data
                and sensor_id not in ucr_static_sensors_data
            }

            removed_sensors = {
                sensor_id
                for sensor_id in current_sensors
                if any(entity_id in sensor_id for entity_id in old_sensors)
            }

            _LOGGER.debug("Current sensors: %s", list(current_sensors.keys()))
            _LOGGER.debug("Active alarms: %s", active_alarms)
            _LOGGER.debug("Active vehicles: %s", active_vehicles)
            _LOGGER.debug("Active static sensors: %s", active_static_sensors)
            _LOGGER.debug("All active sensor IDs: %s", current_sensors)
            _LOGGER.debug("Sensors that should be removed: %s", removed_sensors)

            for sensor_id in removed_sensors:
                if entity_registry.async_is_registered(sensor_id):
                    entity_registry.async_remove(sensor_id)
                    _LOGGER.debug("Removed sensor: %s", sensor_id)
                else:
                    _LOGGER.warning(
                        "Sensor not found in entity registry: %s", sensor_id
                    )

        # Add new sensors to Home Assistant
        if new_sensors:
            async_add_entities(new_sensors)

    # Initial synchronization
    await sync_sensors()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


async def async_remove_sensors(hass: HomeAssistant, cluster_id: str) -> None:
    """Remove all sensors for a specific HUB."""
    if DOMAIN in hass.data and cluster_id in hass.data[DOMAIN]:
        sensors = hass.data[DOMAIN][cluster_id].get("sensors", {})
        for sensor_id, sensor in sensors.items():
            sensor.remove_from_hass()
            _LOGGER.info("Removed sensor: %s for HUB: %s", sensor_id, cluster_id)

        # Entferne die Sensor-Liste
        hass.data[DOMAIN][cluster_id].pop("sensors", None)


class BaseDiveraSensor(Entity):
    """Basisklasse für Divera-Sensoren."""

    def __init__(self, coordinator, ucr_data, ucr_id: str) -> None:
        """Init class BaseDiveraSensor."""
        self.coordinator = coordinator
        self.cluster_id = coordinator.cluster_id
        self.ucr_id = ucr_id
        self.ucr_data = ucr_data

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
            "via_device": (DOMAIN, self.cluster_id),
        }

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        """Registriere Updates."""
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
                sensors = self.hass.data[DOMAIN][self.cluster_id].get("sensors", {})
                if self.entity_id in sensors:
                    del sensors[self.entity_id]
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


class DiveraAlarmSensor(BaseDiveraSensor):
    """Ein Sensor, der einen einzelnen Alarm darstellt."""

    def __init__(self, coordinator, ucr_data, alarm_id: str, cluster_id: str) -> None:
        """Init class DiveraAlarmSensor."""
        super().__init__(coordinator, ucr_data, cluster_id)
        self.alarm_id = alarm_id
        self.alarm_data = self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})

    @property
    def device_info(self):
        """Add sensor to device."""
        self.firstname = self.ucr_data.get(D_USER, {}).get("firstname", "")
        self.lastname = self.ucr_data.get(D_USER, {}).get("lastname", "")
        return {
            "identifiers": {(DOMAIN, f"{self.firstname} {self.lastname}")},
            "name": f"Einheit {self.ucr_id}",
            "manufacturer": MANUFACTURER,
            "model": DOMAIN,
            "sw_version": f"{VERSION}.{MINOR_VERSION}",
            "via_device": (DOMAIN, self.cluster_id),
        }

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"sensor.{sanitize_entity_id(f'{self.ucr_id}_alarm_{self.alarm_id}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        return f"{self.ucr_id}_{self.alarm_id}"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        return f"Alarm ID {self.alarm_id}"

    @property
    def state(self) -> str:
        """Aktueller Zustand des Sensors."""
        alarm_data = self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("title", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute des Sensors."""
        return self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        alarm_data = self.ucr_data.get(D_ALARM, {}).get(self.alarm_id, {})
        closed = alarm_data.get("closed", False)
        priority = alarm_data.get("priority", False)
        if closed:
            return I_CLOSED_ALARM
        if priority:
            return I_OPEN_ALARM

        return I_OPEN_ALARM_NOPRIO


class DiveraVehicleSensor(BaseDiveraSensor):
    """Ein Sensor, der ein einzelnes Fahrzeug darstellt."""

    def __init__(self, coordinator, ucr_data, vehicle_id: str, cluster_id: str) -> None:
        """INit class DiveraVehicleSensor."""
        super().__init__(coordinator, ucr_data, cluster_id)
        self._vehicle_id = vehicle_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"sensor.{sanitize_entity_id(f'{self.ucr_data["ucr_id"]}_vehicle_{self._vehicle_id}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{self.ucr_id}_vehicle_{self._vehicle_id}"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name} "

    @property
    def state(self) -> str:
        """Aktueller Zustand des Sensors."""
        vehicle_data = self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        return vehicle_data.get("fmsstatus_id", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute des Sensors."""
        extra_state_attributes = {}
        extra_state_attributes["Vehicle-ID"] = self._vehicle_id
        extra_state_attributes.update(
            self.ucr_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        )
        return extra_state_attributes

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_VEHICLE


class DiveraFirestationSensor(BaseDiveraSensor):
    """Ein Sensor, der eine Feuerwehrwache darstellt."""

    def __init__(self, coordinator, ucr_data, cluster_id: str) -> None:
        """Init class DiveraFirestationSensor."""
        super().__init__(coordinator, ucr_data, cluster_id)
        self.fs_name = next(iter(ucr_data.get(D_CLUSTER_ADDRESS, {}).keys()), "Unknown")

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"sensor.{sanitize_entity_id(f'{self.ucr_id}_cluster_address')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        fs_name = next(
            iter(self.ucr_data.get(D_CLUSTER_ADDRESS, {}).keys()),
            "Unknown",
        )
        return f"{self.ucr_id}_cluster_address"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        return next(
            iter(self.ucr_data.get(D_CLUSTER_ADDRESS, {}).keys()),
            "Unknown",
        )

    @property
    def state(self) -> str:
        """Aktueller Zustand der Feuerwehrwache."""
        return next(
            iter(self.ucr_data.get(D_CLUSTER_ADDRESS, {}).keys()),
            "Unknown",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute des Sensors."""
        firestation_data = self.ucr_data.get(D_CLUSTER_ADDRESS, {}).get(
            self.fs_name, {}
        )
        address = firestation_data.get("address", {})
        return {
            "cluster_id": self.ucr_id,
            "shortname": firestation_data.get("shortname", "Unknown"),
            "latitude": address.get("lat"),
            "longitude": address.get("lng"),
            "street": address.get("street"),
            "zip": address.get("zip"),
            "city": address.get("city"),
            "country": address.get("country"),
            "ags": address.get("ags"),
        }

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_FIRESTATION


class DiveraAlarmCountSensor(BaseDiveraSensor):
    """Ein Sensor, der die Anzahl der aktiven Alarme darstellt."""

    def __init__(self, coordinator, ucr_data, cluster_id: str) -> None:
        """Init class DiveraAlarmCountSensor."""
        super().__init__(coordinator, ucr_data, cluster_id)

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return f"sensor.{sanitize_entity_id(f'{self.ucr_id}_active_alarm_count')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        return f"{self.ucr_id}_active_alarm_count"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        return f"Open Alarms {self.ucr_id}"

    @property
    def state(self) -> int:
        """Aktueller Zustand des Sensors."""
        try:
            return int(self.ucr_data.get(D_ACTIVE_ALARM_COUNT, 0))
        except (ValueError, TypeError):
            return 0

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_COUNTER_ACTIVE_ALARMS


class DiveraStatusSensor(BaseDiveraSensor):
    """Ein Sensor, der den Status des Nutzers darstellt."""

    def __init__(self, coordinator, ucr_data, ucr_id: str) -> None:
        """Init class DiveraStatusSensor."""
        super().__init__(coordinator, ucr_data, ucr_id)
        self._entity_id = f"sensor.{self.ucr_id}_status"

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        return f"{self.ucr_id}_status"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        unit_name = self.ucr_data.get(D_UCR, {}).get("name", "Unit Unknown")
        return f"Status {unit_name}"

    @property
    def state(self) -> str:
        """Aktueller Zustand des Sensors."""
        status_id = str(self.ucr_data.get(D_STATUS, {}).get("status_id", {}))
        return (
            self.ucr_data.get(D_STATUS_CONF, {})
            .get(status_id, {})
            .get("name", "Unknown")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Rückgabe weiterer Statusdetails."""
        status_options = []
        for status_id, status_details in self.ucr_data.get(D_STATUS_CONF, {}).items():
            status_name = f"{status_details.get("name", "Unknown")} ({status_id})"
            if status_name and status_name not in status_options:
                status_options.append(status_name)

        status_id = str(self.ucr_data.get(D_STATUS, {}).get("status_id", {}))
        # status_id.append(status_id)

        return {
            "status_id": status_id,
            "options": status_options,
        }

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_STATUS
