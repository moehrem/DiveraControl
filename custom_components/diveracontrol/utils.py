"""Handles permission requests."""

import logging
import time
import asyncio
from functools import wraps

import homeassistant.helpers.entity_registry as er
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    D_ACCESS,
    D_COORDINATOR,
    D_CLUSTER_NAME,
    D_USER,
    D_ACCESS,
    # D_HUB_ID,
    D_UCR,
    PERM_MANAGEMENT,
)

LOGGER = logging.getLogger(__name__)


class BaseDiveraEntity:
    """Gemeinsame Basisklasse für Sensoren und Tracker."""

    def __init__(self, coordinator, cluster_id: str) -> None:
        """Initialisiert die gemeinsame Basisklasse."""
        self.coordinator = coordinator
        self.cluster_id = cluster_id
        self.cluster_data = coordinator.cluster_data

    @property
    def device_info(self):
        """Gibt Geräteinformationen zurück."""
        unit_name = self.coordinator.cluster_name
        return {
            "identifiers": {(DOMAIN, unit_name)},
            "name": unit_name,
            "manufacturer": MANUFACTURER,
            "model": DOMAIN,
            "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
            "entry_type": "service",
        }

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
        LOGGER.debug("Starting removal process for entity: %s", self.entity_id)

        # Entferne aus dem Entity-Registry
        try:
            registry = er.async_get(self.hass)
            if registry.async_is_registered(self.entity_id):
                registry.async_remove(self.entity_id)
                LOGGER.debug("Removed entity from registry: %s", self.entity_id)
            else:
                LOGGER.debug("Entity not found in registry: %s", self.entity_id)
        except Exception as e:
            LOGGER.error(
                "Failed to remove entity from registry: %s, Error: %s",
                self.entity_id,
                e,
            )

        # Entferne aus der State-Machine
        try:
            self.hass.states.async_remove(self.entity_id)
            LOGGER.debug("Removed entity from state machine: %s", self.entity_id)
        except Exception as e:
            LOGGER.error(
                "Failed to remove entity from state machine: %s, Error: %s",
                self.entity_id,
                e,
            )

        # Entferne aus internen Datenstrukturen
        try:
            entity_type = (
                "sensors"
                if self.__class__.__name__ == "BaseDiveraSensor"
                else "trackers"
            )

            if DOMAIN in self.hass.data and self.cluster_id in self.hass.data[DOMAIN]:
                entities = self.hass.data[DOMAIN][self.cluster_id].get(entity_type, {})
                if self.entity_id in entities:
                    del entities[self.entity_id]
                    LOGGER.debug(
                        "Removed entity from internal storage: %s", self.entity_id
                    )
        except Exception as e:
            LOGGER.error(
                "Failed to remove entity from internal storage: %s, Error: %s",
                self.entity_id,
                e,
            )

        LOGGER.info("Entity successfully removed: %s", self.entity_id)


def permission_check(hass: HomeAssistant, cluster_id, perm_key):
    """Check permission and return success.

    Args:
        hass: HomeAssistant
        cluster_id: str
        perm_key: str

    Returns:
        bool: True if permission granted, False if denied

    """

    success = False

    coordinator_data = (
        hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR, {})
    )

    if coordinator_data is not None and perm_key is not None:
        cluster_name = coordinator_data.cluster_name
        management = (
            coordinator_data.cluster_data.get(D_USER, {})
            .get(D_ACCESS, {})
            .get(PERM_MANAGEMENT)
        )
        permission = (
            coordinator_data.cluster_data.get(D_USER, {})
            .get(D_ACCESS, {})
            .get(perm_key)
        )

        if management:
            success = management
        elif permission:
            success = permission
        else:
            success = False

        if not success:
            # raise DiveraPermissionDenied(
            #     f"Permission denied for {perm_key} in cluster {cluster_name}"
            # )
            LOGGER.warning(
                "Permission denied for %s in cluster %s", perm_key, cluster_name
            )

    return success


def get_device_info(cluster_name):
    """Gibt Geräteinformationen für den Tracker zurück."""
    unit_name = cluster_name
    return {
        "identifiers": {(DOMAIN, unit_name)},
        "name": unit_name,
        "manufacturer": MANUFACTURER,
        "model": DOMAIN,
        "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        "entry_type": "service",
    }


def log_execution_time(func):
    """Decorator to log execution time of functions (sync & async)."""

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            LOGGER.debug(
                "Execution time of %s: %.2f seconds", func.__name__, elapsed_time
            )
            return result

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            LOGGER.debug(
                "Execution time of %s: %.2f seconds", func.__name__, elapsed_time
            )
            return result

        return sync_wrapper


def get_cluster_id(hass: HomeAssistant, sensor_id: str):
    """Fetch cluster_id based on sensor_id. Raises exception if not found."""
    try:
        for cluster_id, cluster_data in hass.data[DOMAIN].items():
            for sensor in cluster_data["sensors"]:
                if sensor == str(sensor_id):
                    return cluster_id
            for tracker in cluster_data["device_tracker"]:
                if tracker == str(sensor_id):
                    return cluster_id
    except KeyError:
        error_message = f"Cluster-ID not found for Sensor-ID {sensor_id}"
        LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from None


def get_api_instance(hass: HomeAssistant, sensor_id: str):
    """Fetch api-instance of hub based on sensor_id or cluster_id. Raises exception if not found."""
    try:
        # try finding cluster_id with given sensor_id
        for cluster_id, cluster_data in hass.data[DOMAIN].items():
            for sensor in cluster_data["sensors"]:
                if sensor == str(sensor_id):
                    api_instance = hass.data[DOMAIN][str(cluster_id)]["api"]

        # if nothing found, try sensor_id as cluster_id
        for cluster_id in hass.data[DOMAIN]:
            if cluster_id == sensor_id:
                api_instance = hass.data[DOMAIN][str(cluster_id)]["api"]

        return api_instance

    except KeyError:
        error_message = f"API-instance not found for Sensor-ID {sensor_id}"
        LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from None


def get_coordinator_data(hass: HomeAssistant, sensor_id: str) -> dict[str, any]:
    """Holt die Koordinatordaten für die gegebene cluster_id oder wirft eine Exception."""
    try:
        # try finding cluster_id with given sensor_id
        for cluster_id, cluster_data in hass.data[DOMAIN].items():
            for sensor in cluster_data["sensors"]:
                if sensor == str(sensor_id):
                    coordinator_data = (
                        hass.data.get(DOMAIN, {})
                        .get(str(cluster_id), "")
                        .get(D_COORDINATOR)
                    )

        return coordinator_data

    except KeyError:
        error_message = f"Coordinator data not found for Sensor-ID {sensor_id}"
        LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from None


class DiveraAPIError(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        LOGGER.error("Authentifizierung bei Divera fehlgeschlagen: %s", str(error))


class DiveraPermissionDenied(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        LOGGER.warning("Zugriff auf Divera-API verweigert: %s", str(error))


async def handle_entity(hass: HomeAssistant, call: dict, service: str):
    """Update entity data based on given method."""

    match service:
        case "put_alarm" | "post_close_alarm":
            alarm_id = call.data.get("alarm_id")
            cluster_id = get_cluster_id(hass, alarm_id)
            sensor_entity_id = f"sensor.{cluster_id}_alarm_{alarm_id}"
            tracker_entity_id = f"sensor.{cluster_id}_alarmtracker_{alarm_id}"

            for entity in hass.data[DOMAIN][str(cluster_id)]["sensors"].values():
                if entity.entity_id == sensor_entity_id:
                    # for key, value in call.data.items():
                    #     await entity.async_update_state(key, value)
                    await entity.async_update_state(call.data)
                    break

            for entity in hass.data[DOMAIN][str(cluster_id)]["device_tracker"].values():
                if entity.entity_id == tracker_entity_id:
                    # for key, value in call.data.items():
                    #     await entity.async_update_state(key, value)
                    await entity.async_update_state(call.data)
                    break

        case "post_vehicle_status" | "post_using_vehicle_property":
            vehicle_id = call.data.get("vehicle_id")
            cluster_id = get_cluster_id(hass, vehicle_id)
            sensor_entity_id = f"sensor.{cluster_id}_vehicle_{vehicle_id}"
            tracker_entity_id = (
                f"device_tracker.{cluster_id}_vehicletracker_{vehicle_id}"
            )

            for entity in hass.data[DOMAIN][str(cluster_id)]["sensors"].values():
                if entity.entity_id == sensor_entity_id:
                    # for key, value in call.data.items():
                    #     await entity.async_update_state(key, value)
                    await entity.async_update_state(call.data)
                    break

            for entity in hass.data[DOMAIN][str(cluster_id)]["device_tracker"].values():
                if entity.entity_id == tracker_entity_id:
                    # for key, value in call.data.items():
                    #     await entity.async_update_state(key, value)
                    await entity.async_update_state(call.data)
                    break

        case _:  # default
            LOGGER.error("Service not found: %s", service)
            raise HomeAssistantError(f"Service not found: {service}")
