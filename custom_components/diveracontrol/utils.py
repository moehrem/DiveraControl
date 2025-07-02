"""Contain several helper methods for DiveraControl integration."""

import asyncio
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
import logging
import time
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.translation import async_get_translations

from .const import (
    D_ACCESS,
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
    D_VEHICLE,
    DOMAIN,
    MANUFACTURER,
    MINOR_VERSION,
    PERM_MANAGEMENT,
    VERSION,
)

if TYPE_CHECKING:
    from .coordinator import DiveraCoordinator
    from .divera_api import DiveraAPI

_LOGGER = logging.getLogger(__name__)
_translation_cache = {}


def permission_check(
    hass: HomeAssistant,
    ucr_id: str,
    perm_key: str,
) -> bool:
    """Check permission and return success.

    Args:
        hass: HomeAssistant
        ucr_id: str
        perm_key: str

    Returns:
        bool: True if permission granted, False if denied

    """

    success = False

    coordinator_data = hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR, {})

    if coordinator_data is not None and perm_key is not None:
        cluster_name = coordinator_data.admin_data[D_CLUSTER_NAME]
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
            _LOGGER.debug(
                "Permission denied for %s in cluster %s", perm_key, cluster_name
            )

    return success


def get_device_info(cluster_name: str) -> DeviceInfo:
    """Return device information, used in sensor and tracker base classes."""
    return {
        "identifiers": {(DOMAIN, cluster_name)},
        "name": cluster_name,
        "manufacturer": MANUFACTURER,
        "model": DOMAIN,
        "sw_version": f"{VERSION}.{MINOR_VERSION}",
        "entry_type": "service",  # type: ignore[misc]
    }


def log_execution_time(func: Callable) -> Callable:
    """Log execution times of function only if loglevel is DEBUG.

    Args:
        func (callable): the function to be wrapped.

    Returns:
        callable: the wrapped function.

    """

    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return func

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            _LOGGER.debug(
                "Execution time of %s: %.2f seconds", func.__name__, elapsed_time
            )
            return result

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        _LOGGER.debug("Execution time of %s: %.2f seconds", func.__name__, elapsed_time)
        return result

    return sync_wrapper


def get_ucr_id(
    hass: HomeAssistant,
    sensor_id: str,
) -> str:
    """Fetch ucr_id based on sensor_id. Raises exception if not found.

    Args:
        hass (HomeAssistant): Home Assistant instance
        sensor_id (str): Sensor ID to search for

    Returns:
        str: ucr_id (user_cluster_relation) associated with the sensor_id

    """

    try:
        for ucr_id, cluster_data in hass.data[DOMAIN].items():
            if sensor_id in cluster_data.get("sensors", []):
                return ucr_id
            if sensor_id in cluster_data.get("device_tracker", []):
                return ucr_id

    except KeyError:
        pass  # behandelt unten im Fehlerfall

    error_message = f"Cluster-ID not found for Sensor-ID {sensor_id}"
    _LOGGER.error(error_message)
    raise HomeAssistantError(error_message)


# def get_api_instance(
#     hass: HomeAssistant,
#     sensor_id: str,
# ) -> "DiveraAPI":
#     """Fetch api-instance of hub based on sensor_id or ucr_id. Raises exception if not found."""

#     api_instance = None

#     try:
#         # try finding ucr_id with given sensor_id
#         for cluster_data in hass.data[DOMAIN].values():
#             for sensor in cluster_data["sensors"]:
#                 if sensor == sensor_id:
#                     api_instance = cluster_data["api"]
#                     break

#         # if nothing found, try sensor_id as ucr_id
#         if api_instance is None:
#             for ucr_id, cluster_data in hass.data[DOMAIN].items():
#                 if ucr_id == int(sensor_id):
#                     api_instance = cluster_data["api"]
#                     break

#         if api_instance is None:
#             raise KeyError

#     except KeyError:
#         error_message = f"API-instance not found for Sensor-ID {sensor_id}"
#         _LOGGER.error(error_message)
#         raise HomeAssistantError(error_message) from None

#     return api_instance


def get_api_instance(
    hass: HomeAssistant,
    sensor_id: str | int,
) -> "DiveraAPI":
    """Fetch api-instance of hub based on sensor_id or ucr_id. Raises exception if not found.

    Args:
        hass: HomeAssistant instance
        sensor_id: Sensor ID or ucr_id (str or int)

    Returns:
        DiveraAPI: API instance for the given sensor or ucr_id

    Raises:
        HomeAssistantError: If integration data or API instance is missing or not found
    """

    try:
        domain_data = hass.data[DOMAIN]
    except KeyError as exc:
        error_message = f"Integration data missing in hass.data for domain {DOMAIN}"
        _LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from exc

    # Try finding api instance by sensor_id in sensors
    for cluster_data in domain_data.values():
        sensors = cluster_data.get("sensors", [])
        if str(sensor_id) in sensors or sensor_id in sensors:
            api_instance = cluster_data.get("api")
            if api_instance is not None:
                return api_instance
            error_message = f"API instance missing for sensor {sensor_id}"
            _LOGGER.error(error_message)
            raise HomeAssistantError(error_message)

    # Try finding api instance by sensor_id as cluster_id (int or str)
    possible_keys = {sensor_id}

    if not isinstance(sensor_id, int):
        try:
            possible_keys.add(int(sensor_id))
        except (ValueError, TypeError):
            _LOGGER.debug("sensor_id '%s' konnte nicht in int umgewandelt werden", sensor_id)

    possible_keys.add(str(sensor_id))

    for key in possible_keys:
        cluster_data = domain_data.get(key)
        if cluster_data:
            api_instance = cluster_data.get("api")
            if api_instance is not None:
                return api_instance
            error_message = f"API instance missing for ucr_id {key}"
            _LOGGER.error(error_message)
            raise HomeAssistantError(error_message)

    error_message = f"API instance not found for sensor_id {sensor_id}"
    _LOGGER.error(error_message)
    raise HomeAssistantError(error_message)


def get_coordinator_data(
    hass: HomeAssistant,
    sensor_id: str,
) -> "DiveraCoordinator":
    """Fetch coordinator data based on sensor id.

    Args:
        hass (HomeAssistant): Home Assistant instance
        sensor_id (str): sensor ID to search for

    Returns:
        DiveraCoordinator: DiveraControl coordinator instance of DiveraControl

    """
    coordinator_data = None

    try:
        # try finding ucr_id with given sensor_id
        for ucr_id, cluster_data in hass.data[DOMAIN].items():
            for sensor in cluster_data["sensors"]:
                if sensor == sensor_id:
                    coordinator_data = (
                        hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR)
                    )
                    break
            if coordinator_data:
                break

        if coordinator_data is None:
            raise KeyError

    except KeyError:
        error_message = f"Coordinator data not found for Sensor-ID {sensor_id}"
        _LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from None

    return coordinator_data


async def handle_entity(
    hass: HomeAssistant,
    call: ServiceCall,
    service: str,
) -> None:
    """Update entity data based on given method.

    Args:
        hass (HomeAssistant): Home Assistant instance
        call (dict): Data from service call
        service (str): Service name that was called

    Returns:
        None

    """

    match service:
        case "put_alarm" | "post_close_alarm":
            alarm_id: str = call.data.get("alarm_id") or ""
            ucr_id = get_ucr_id(hass, alarm_id)
            coordinator = hass.data[DOMAIN].get(ucr_id, {}).get(D_COORDINATOR, None)

            if not coordinator:
                _LOGGER.error("Can't find coordinator for unit %s", ucr_id)
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
            vehicle_id: str = call.data.get("vehicle_id") or ""
            ucr_id = get_ucr_id(hass, vehicle_id)
            coordinator = hass.data[DOMAIN].get(ucr_id, {}).get(D_COORDINATOR, None)

            if not coordinator:
                _LOGGER.error("Can't find coordinator for unit %s", ucr_id)
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


def set_update_interval(
    old_interval: timedelta | None,
    open_alarms: int,
    admin_data: dict[str, Any],
) -> timedelta:
    """Set update interval based on open alarms.

    Args:
        old_interval (timedelta | None): current update interval.
        open_alarms (int): number of open alarms.
        admin_data (dict): admin data of coordinator containing update interval configuration.

    Returns:
        timedelta: new update interval.

    """

    new_interval = (
        admin_data[D_UPDATE_INTERVAL_ALARM]
        if open_alarms > 0
        else admin_data[D_UPDATE_INTERVAL_DATA]
    )
    cluster_name = admin_data[D_CLUSTER_NAME]

    if old_interval is None or old_interval != new_interval:
        _LOGGER.debug(
            "Update interval changed to %s for unit '%s'",
            new_interval,
            cluster_name,
        )
        return new_interval

    _LOGGER.debug(
        "Update interval not changed, still %s for unit '%s'",
        old_interval,
        cluster_name,
    )

    return old_interval


def extract_keys(data) -> set[str]:
    """Extract keys from dictionaries."""
    return set(data.keys()) if isinstance(data, dict) else set()


async def get_translation(
    hass: HomeAssistant,
    category: str,
    language=None,
) -> dict[str, str]:
    """Load and cache translations.

    Args:
        hass (HomeAssistant): Home Assistant instance
        category (str): category of translation to be loaded
        language (str, optional): language code, defaults to None

    """

    if language is None:
        language = hass.config.language

    cache_key = (DOMAIN, category, language)
    if cache_key not in _translation_cache:
        _translation_cache[cache_key] = await async_get_translations(
            hass,
            language,
            category=category,
            integrations=[DOMAIN],
        )
    return _translation_cache[cache_key]
