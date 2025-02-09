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
    # new structure
    D_STATUS,
    D_STATUS_CONF,
    D_UCR,
    D_VEHICLE,
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
)
from .utils import sanitize_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up the Divera sensors."""

    hub = config_entry.data
    hub_id = hub[D_UCR]
    coordinator = hass.data[DOMAIN][hub_id]["coordinator"]
    current_sensors = hass.data[DOMAIN][hub_id].setdefault("sensors", {})

    async def sync_sensors():
        """Synchronize all sensors with the current data from the API."""
        new_sensors = []
        active_alarms = coordinator.data.get(D_ALARM, {})
        active_vehicles = coordinator.data.get(D_VEHICLE, {})
        active_static_sensors = {D_ACTIVE_ALARM_COUNT, D_CLUSTER_ADDRESS, D_STATUS}

        if isinstance(active_alarms, dict):
            active_alarms = set(active_alarms.keys())
        else:
            active_alarms = set()

        if isinstance(active_vehicles, dict):
            active_vehicles = set(active_vehicles.keys())
        else:
            active_vehicles = set()

        # Add or update status sensors
        static_sensor_map = {
            D_ACTIVE_ALARM_COUNT: DiveraAlarmCountSensor(coordinator, hub_id),
            D_CLUSTER_ADDRESS: DiveraFirestationSensor(coordinator, hub_id),
            D_STATUS: DiveraStatusSensor(coordinator, hub_id),
        }
        for sensor_name, sensor_instance in static_sensor_map.items():
            if sensor_name not in current_sensors:
                _LOGGER.debug("Adding static sensor: %s", sensor_name)
                new_sensors.append(sensor_instance)
                current_sensors[sensor_name] = sensor_instance

        # Add new alarm sensors
        new_alarms = active_alarms - current_sensors.keys()
        for alarm_id in new_alarms:
            sensor = DiveraAlarmSensor(coordinator, alarm_id, hub_id)
            _LOGGER.debug("Adding alarm sensor: %s", alarm_id)
            new_sensors.append(sensor)
            current_sensors[alarm_id] = sensor

        # Add new vehicle sensors
        new_vehicles = active_vehicles - current_sensors.keys()
        for vehicle_id in new_vehicles:
            sensor = DiveraVehicleSensor(coordinator, vehicle_id, hub_id)
            _LOGGER.debug("Adding vehicle sensor: %s", vehicle_id)
            new_sensors.append(sensor)
            current_sensors[vehicle_id] = sensor

        # Remove outdated sensors
        active_ids = active_alarms | active_vehicles | active_static_sensors
        removed_sensors = set(current_sensors.keys()) - active_ids
        for sensor_id in removed_sensors:
            sensor = current_sensors.pop(sensor_id, None)
            if sensor:
                await sensor.remove_from_hass()
                _LOGGER.debug("Removed sensor: %s", sensor_id)

        # Add new sensors to Home Assistant
        if new_sensors:
            async_add_entities(new_sensors)

    # Initial synchronization
    await sync_sensors()

    # Add listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


async def async_remove_sensors(hass: HomeAssistant, hub_id: str) -> None:
    """Remove all sensors for a specific HUB."""
    if DOMAIN in hass.data and hub_id in hass.data[DOMAIN]:
        sensors = hass.data[DOMAIN][hub_id].get("sensors", {})
        for sensor_id, sensor in sensors.items():
            sensor.remove_from_hass()
            _LOGGER.info("Removed sensor: %s for HUB: %s", sensor_id, hub_id)

        # Entferne die Sensor-Liste
        hass.data[DOMAIN][hub_id].pop("sensors", None)


class BaseDiveraSensor(Entity):
    """Basisklasse für Divera-Sensoren."""

    def __init__(self, coordinator, hub_id: str) -> None:
        """Init class BaseDiveraSensor."""
        self.coordinator = coordinator
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
            if DOMAIN in self.hass.data and self.hub_id in self.hass.data[DOMAIN]:
                sensors = self.hass.data[DOMAIN][self.hub_id].get("sensors", {})
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

    def __init__(self, coordinator, alarm_id: str, hub_id: str) -> None:
        """Init class DiveraAlarmSensor."""
        super().__init__(coordinator, hub_id)
        self.alarm_id = alarm_id
        self.alarm_data = self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        return f"{self.hub_id}_{self.alarm_id}"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        return f"Alarm ID {self.alarm_id}"

    @property
    def state(self) -> str:
        """Aktueller Zustand des Sensors."""
        alarm_data = self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})
        return alarm_data.get("title", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute des Sensors."""
        return self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        alarm_data = self.coordinator.data.get(D_ALARM, {}).get(self.alarm_id, {})
        closed = alarm_data.get("closed", False)
        priority = alarm_data.get("priority", False)
        if closed:
            return I_CLOSED_ALARM
        if priority:
            return I_OPEN_ALARM

        return I_OPEN_ALARM_NOPRIO


class DiveraVehicleSensor(BaseDiveraSensor):
    """Ein Sensor, der ein einzelnes Fahrzeug darstellt."""

    def __init__(self, coordinator, vehicle_id: str, hub_id: str) -> None:
        """INit class DiveraVehicleSensor."""
        super().__init__(coordinator, hub_id)
        self._vehicle_id = vehicle_id

    @property
    def entity_id(self) -> str:
        """Entitäts-ID des Sensors."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"sensor.{sanitize_entity_id(f'vehicle_{shortname}_{veh_name}')}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Setze die Entitäts-ID des Sensors."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        return f"{vehicle_data.get("name", "Unknown")}_{self._vehicle_id}"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name} "

    @property
    def state(self) -> str:
        """Aktueller Zustand des Sensors."""
        vehicle_data = self.coordinator.data.get(D_VEHICLE, {}).get(
            self._vehicle_id, {}
        )
        return vehicle_data.get("fmsstatus_id", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute des Sensors."""
        return self.coordinator.data.get(D_VEHICLE, {}).get(self._vehicle_id, {})

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_VEHICLE


class DiveraFirestationSensor(BaseDiveraSensor):
    """Ein Sensor, der eine Feuerwehrwache darstellt."""

    def __init__(self, coordinator, hub_id: str) -> None:
        """Init class DiveraFirestationSensor."""
        super().__init__(coordinator, hub_id)
        self.fs_name = next(
            iter(coordinator.data.get(D_CLUSTER_ADDRESS, {}).keys()), "Unknown"
        )

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        fs_name = next(
            iter(self.coordinator.data.get(D_CLUSTER_ADDRESS, {}).keys()), "Unknown"
        )
        return f"{self.hub_id}_firestation_{fs_name}"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        return next(
            iter(self.coordinator.data.get(D_CLUSTER_ADDRESS, {}).keys()), "Unknown"
        )

    @property
    def state(self) -> str:
        """Aktueller Zustand der Feuerwehrwache."""
        return next(
            iter(self.coordinator.data.get(D_CLUSTER_ADDRESS, {}).keys()), "Unknown"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute des Sensors."""
        firestation_data = self.coordinator.data.get(D_CLUSTER_ADDRESS, {}).get(
            self.fs_name, {}
        )
        address = firestation_data.get("address", {})
        return {
            "hub_id": self.hub_id,
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

    def __init__(self, coordinator, hub_id: str) -> None:
        """Init class DiveraAlarmCountSensor."""
        super().__init__(coordinator, hub_id)

    @property
    def unique_id(self) -> str:
        """Eindeutige ID des Sensors."""
        return f"{self.hub_id}_active_alarm_count"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        return f"Open Alarms {self.hub_id}"

    @property
    def state(self) -> int:
        """Aktueller Zustand des Sensors."""
        try:
            return int(self.coordinator.data.get(D_ACTIVE_ALARM_COUNT, 0))
        except (ValueError, TypeError):
            return 0

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_COUNTER_ACTIVE_ALARMS


class DiveraStatusSensor(BaseDiveraSensor):
    """Ein Sensor, der den Status des Nutzers darstellt."""

    def __init__(self, coordinator, hub_id: str) -> None:
        """Init class DiveraStatusSensor."""
        super().__init__(coordinator, hub_id)
        self._entity_id = f"sensor.status_{self.hub_id}"

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
        return f"status_{self.hub_id}"

    @property
    def name(self) -> str:
        """Name des Sensors."""
        unit_name = (
            self.coordinator.data.get(D_UCR, {})
            .get(self.hub_id, "")
            .get("name", "Unit Unknown")
        )
        return f"Status {unit_name}"

    @property
    def state(self) -> str:
        """Aktueller Zustand des Sensors."""
        status_id = str(self.coordinator.data.get(D_STATUS, {}).get("status_id", {}))
        return (
            self.coordinator.data.get(D_STATUS_CONF, {})
            .get(status_id, {})
            .get("name", "Unknown")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Rückgabe weiterer Statusdetails."""
        status_options = []
        for status_id, status_details in self.coordinator.data.get(
            D_STATUS_CONF, {}
        ).items():
            status_name = f"{status_details.get("name", "Unknown")} ({status_id})"
            if status_name and status_name not in status_options:
                status_options.append(status_name)

        status_id = str(self.coordinator.data.get(D_STATUS, {}).get("status_id", {}))
        # status_id.append(status_id)

        return {
            "status_id": status_id,
            "options": status_options,
        }

    @property
    def icon(self) -> str:
        """Icon des Sensors."""
        return I_STATUS
