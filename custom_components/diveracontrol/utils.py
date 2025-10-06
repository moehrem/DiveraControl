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
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    D_ACCESS,
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
    D_VEHICLE,
    DOMAIN,
    MANUFACTURER,
    MINOR_VERSION,
    PATCH_VERSION,
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
        "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        "entry_type": "service",  # type: ignore[misc]
        "configuration_url": "https://app.divera247.com/session/login.html",
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


def _normalize_id_list(value: Any) -> list[str]:
    """Normalize device_id or entity_id to a list of strings.

    Handles:
    - Single string: "device_123" -> ["device_123"]
    - Comma-separated string: "device_123,device_456" -> ["device_123", "device_456"]
    - List of strings: ["device_123", "device_456"] -> ["device_123", "device_456"]
    - Empty/None: [] -> []
    """
    if not value:
        return []

    if isinstance(value, str):
        # Handle comma-separated strings
        return [item.strip() for item in value.split(",") if item.strip()]

    if isinstance(value, list):
        # Handle list of strings (flatten any comma-separated items)
        result = []
        for item in value:
            if isinstance(item, str):
                result.extend(
                    subitem.strip() for subitem in item.split(",") if subitem.strip()
                )
            else:
                result.append(str(item))
        return result

    # Single non-string value
    return [str(value)]


def get_api_instances(
    hass: HomeAssistant,
    device_ids: list[str],
    entity_ids: list[str],
) -> list["DiveraAPI"]:
    """Fetch api-instance of devices based on device_ids and/or entity_ids given from user input. Raises exception if not found. Handles duplicates by using a dict.

    Args:
        hass: HomeAssistant instance
        device_ids: List of device IDs to search for
        entity_ids: List of entity IDs to search for

    Returns:
        api_instances: API instances as list of classes of DiveraAPI

    Raises:
        HomeAssistantError: If integration data or API instance is missing or not found
    """

    api_instances_dict: dict[str, DiveraAPI] = {}
    device_registry = dr.async_get(hass)

    # handle device_ids
    if device_ids:
        device_ids = _normalize_id_list(device_ids)

        for device_id in device_ids:
            device = device_registry.devices.get(device_id)
            if not device:
                raise HomeAssistantError(f"Device {device_id} not found")

            entry_id = next(iter(device.config_entries))
            config_entry = hass.config_entries.async_get_entry(entry_id)

            if not config_entry:
                raise HomeAssistantError(f"No config entry for device {device_id}")

            ucr_id = config_entry.data.get(D_UCR_ID)

            if not ucr_id:
                raise HomeAssistantError(f"No ucr_id found for device {device_id}")

            api_instance = hass.data["diveracontrol"][ucr_id]["api"]

            api_instances_dict[ucr_id] = api_instance

    # handle entity_ids
    if entity_ids:
        entity_ids = _normalize_id_list(entity_ids)
        entity_registry = er.async_get(hass)
        for entity_id in entity_ids:
            entity_entry = entity_registry.entities.get(entity_id)
            if not entity_entry:
                raise HomeAssistantError(f"Entity {entity_id} not found")

            entry_id = entity_entry.config_entry_id
            config_entry = hass.config_entries.async_get_entry(entry_id)

            if not config_entry:
                raise HomeAssistantError(f"No config entry for entity {entity_id}")

            ucr_id = config_entry.data.get(D_UCR_ID)

            if not ucr_id:
                raise HomeAssistantError(
                    f"No user cluster relation found for entity {entity_id}"
                )

            api_instance = hass.data["diveracontrol"][ucr_id]["api"]

            api_instances_dict[ucr_id] = api_instance

    return list(api_instances_dict.values())


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
    ucr_id: str,
    entity_id: int | str,
) -> None:
    """Update entity data based on given method.

    Args:
        hass (HomeAssistant): Home Assistant instance
        call (dict): Data from service call
        service (str): Service name that was called
        ucr_id (str): User cluster relation ID
        entity_id (int): Entity ID if needed

    Returns:
        None

    """

    entity_id = str(entity_id)

    match service:
        case "put_alarm" | "post_close_alarm":
            coordinator = hass.data[DOMAIN].get(ucr_id, {}).get(D_COORDINATOR, None)

            if not coordinator:
                _LOGGER.error("Can't find coordinator for unit %s", ucr_id)
                return

            alarm_data = (
                coordinator.cluster_data.get(D_ALARM, {})
                .get("items", {})
                .get(str(entity_id), {})
            )

            for key in call.data:
                if key in alarm_data:
                    alarm_data[key] = call.data[key]

            # updating coordinator data
            coordinator.async_set_updated_data(coordinator.cluster_data)

        case "post_vehicle_status" | "post_using_vehicle_property":
            coordinator = hass.data[DOMAIN].get(ucr_id, {}).get(D_COORDINATOR, None)

            if not coordinator:
                _LOGGER.error("Can't find coordinator for unit %s", ucr_id)
                return

            vehicle_data = (
                coordinator.cluster_data.get(D_CLUSTER, {})
                .get(D_VEHICLE, {})
                .get(str(entity_id), {})
            )

            for key in call.data:
                if key in ["status", "status_id"]:
                    vehicle_data["fmsstatus_id"] = call.data[key]
                    continue
                if key in vehicle_data:
                    vehicle_data[key] = call.data[key]

            # updating coordinator data
            coordinator.async_set_updated_data(coordinator.cluster_data)

        case "post_using_vehicle_crew":
            # TODO add entity update with crew
            pass

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
