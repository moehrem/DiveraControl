"""Contain different helper methods."""

import logging
import time
import asyncio
from functools import wraps

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    D_ACCESS,
    D_ALARM,
    D_CLUSTER,
    D_OPEN_ALARMS,
    D_COORDINATOR,
    D_CLUSTER_NAME,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
    D_ACCESS,
    D_VEHICLE,
    # D_HUB_ID,
    D_UCR,
    PERM_MANAGEMENT,
)

_LOGGER = logging.getLogger(__name__)


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
            _LOGGER.warning(
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
            _LOGGER.debug(
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
            _LOGGER.debug(
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
        _LOGGER.error(error_message)
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
        _LOGGER.error(error_message)
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
        _LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from None


class DiveraAPIError(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        _LOGGER.error("Authentifizierung bei Divera fehlgeschlagen: %s", str(error))


class DiveraPermissionDenied(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        _LOGGER.warning("Zugriff auf Divera-API verweigert: %s", str(error))


async def handle_entity(hass: HomeAssistant, call: dict, service: str):
    """Update entity data based on given method."""

    match service:
        case "put_alarm" | "post_close_alarm":
            alarm_id = call.data.get("alarm_id")
            cluster_id = get_cluster_id(hass, alarm_id)
            coordinator = hass.data[DOMAIN].get(cluster_id, {}).get(D_COORDINATOR, None)

            if not coordinator:
                _LOGGER.error("Can't find coordinator for unit %s", cluster_id)
                return

            alarm_data = (
                coordinator.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(str(alarm_id), {})
            )

            for key in call.data:
                if key in alarm_data:
                    alarm_data[key] = call.data[key]

            # updating coordinator data
            coordinator.async_set_updated_data(coordinator.cluster_data)

        case "post_vehicle_status" | "post_using_vehicle_property":
            vehicle_id = call.data.get("vehicle_id")
            cluster_id = get_cluster_id(hass, vehicle_id)
            coordinator = hass.data[DOMAIN].get(cluster_id, {}).get(D_COORDINATOR, None)

            if not coordinator:
                _LOGGER.error("Can't find coordinator for unit %s", cluster_id)
                return

            vehicle_data = (
                coordinator.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(str(vehicle_id), {})
            )

            for key in call.data:
                if key in ["status", "status_id"]:
                    vehicle_data["fmsstatus_id"] = call.data[key]
                    continue
                if key in vehicle_data:
                    vehicle_data[key] = call.data[key]

            # updating coordinator data
            coordinator.async_set_updated_data(coordinator.cluster_data)

        case _:  # default
            _LOGGER.error("Service not found: %s", service)
            raise HomeAssistantError(f"Service not found: {service}")


def check_timestamp(old_data, new_data):
    """Check if new data has a more recent timestamp than old data."""
    try:
        old_ts = old_data.get("ts", 0)
        if old_ts == 0:
            return True

        new_ts = new_data.get("ts", 0)

    except AttributeError as e:
        _LOGGER.debug("Timestamp check failed due to missing attributes: %s", e)
        return True

    else:
        return new_ts > old_ts


def set_update_interval(old_interval, open_alarms, admin_data, cluster_name):
    """Set update interval based on open alarms."""
    # Wähle das richtige Intervall basierend auf der Alarmanzahl
    interval_data = admin_data[D_UPDATE_INTERVAL_DATA]
    interval_alarm = admin_data[D_UPDATE_INTERVAL_ALARM]

    new_interval = interval_alarm if open_alarms > 0 else interval_data

    if old_interval != new_interval:
        _LOGGER.debug(
            "Update interval changed to %s seconds for unit '%s'",
            new_interval,
            cluster_name,
        )
        return new_interval

    return old_interval
