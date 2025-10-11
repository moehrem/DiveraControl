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
from homeassistant.helpers import translation
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
    D_OPEN_ALARMS,
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

    cluster_data = hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR, {}).data
    cluster_name = (
        hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR, {}).cluster_name
    )
    if cluster_data is not None:
        management = cluster_data.get(D_USER, {}).get(D_ACCESS, {}).get(PERM_MANAGEMENT)
        permission = cluster_data.get(D_USER, {}).get(D_ACCESS, {}).get(perm_key)

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


def log_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
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


def get_api_instance_per_device(
    hass: HomeAssistant, device_id: list[str]
) -> list["DiveraAPI"]:
    """Fetch api-instance of devices based on device_ids and/or entity_ids given from user input. Raises exception if not found. Handles duplicates by using a dict.

    Args:
        hass: HomeAssistant instance
        device_ids: List of device IDs to search for

    Returns:
        api_instances: API instances as list of classes of DiveraAPI

    Raises:
        HomeAssistantError: If integration data or API instance is missing or not found
    """

    device_registry = dr.async_get(hass)

    # handle device_ids
    device = device_registry.devices.get(device_id)
    if not device:
        msg = get_translation(
            hass,
            "exceptions",
            "api_device_not_found.message",
            {"device_id": device_id},
        )
        raise HomeAssistantError(msg)

    entry_id = next(iter(device.config_entries))
    config_entry = hass.config_entries.async_get_entry(entry_id)

    if not config_entry:
        msg = get_translation(
            hass,
            "exceptions",
            "api_config_entry_not_found.message",
            {"device_id": device_id},
        )
        raise HomeAssistantError(msg)

    ucr_id = config_entry.data.get(D_UCR_ID)

    if not ucr_id:
        msg = get_translation(
            hass,
            "exceptions",
            "api_ucr_id_not_found.message",
            {"entry_id": entry_id},
        )
        raise HomeAssistantError(msg)

    api_instance = hass.data[DOMAIN][ucr_id]["api"]
    if not api_instance:
        msg = get_translation(
            hass,
            "exceptions",
            "api_instance_not_found.message",
            {"device_id": device_id},
        )
        raise HomeAssistantError(msg)

    return api_instance


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
    coordinator = hass.data[DOMAIN].get(ucr_id, {}).get(D_COORDINATOR, None)

    match service:
        case "put_alarm" | "post_close_alarm":
            alarm_data = (
                coordinator.data.get(D_ALARM, {})
                .get("items", {})
                .get(str(entity_id), {})
            )

            for key in call.data:
                if key in alarm_data:
                    alarm_data[key] = call.data[key]

            # updating coordinator data
            coordinator.async_set_updated_data(coordinator.data)

        case "post_vehicle_status" | "post_using_vehicle_property":
            vehicle_data = (
                coordinator.data.get(D_CLUSTER, {})
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
            coordinator.async_set_updated_data(coordinator.data)

        case "post_using_vehicle_crew":
            # TODO add entity update with crew
            pass

        case _:  # default
            _LOGGER.error("Service not found: %s", service)
            raise HomeAssistantError(f"Service not found: {service}")


def set_update_interval(
    cluster_data: dict[str, Any],
    intervall_data: dict[str, Any],
    old_interval: timedelta | None,
) -> timedelta:
    """Set update interval based on open alarms.

    Args:
        cluster_data (dict): cluster data of coordinator containing update interval configuration.

    Returns:
        timedelta: new update interval.

    """
    alarm_items = cluster_data.get(D_ALARM, {}).get("items", {})
    cluster_name = cluster_data.get(D_CLUSTER_NAME, "Unknown")

    if alarm_items:
        open_alarms = sum(
            1
            for alarm_details in alarm_items.values()
            if not alarm_details.get("closed", True)
        )
        cluster_data.setdefault(D_ALARM, {})[D_OPEN_ALARMS] = open_alarms
    else:
        open_alarms = 0

    new_interval = (
        intervall_data.get(D_UPDATE_INTERVAL_ALARM)
        if open_alarms > 0
        else intervall_data.get(D_UPDATE_INTERVAL_DATA)
    )

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
    key: str,
    placeholders: dict[str, Any] | None = None,
) -> str:
    """Get translated message.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        category (str): Translation category to look up.
        key (str): Translation key to look up.
        placeholders (dict[str, Any] | None): Optional placeholders for formatting the translation string.

    Returns:
        str: The translated string, formatted with placeholders if provided.

    Raises:
        KeyError: If a placeholder in the translation string is not found in the provided placeholders.
    """

    translation_cat = await async_get_translations(
        hass, hass.config.language, category, {DOMAIN}
    )

    key = f"component.{DOMAIN}.{category}.{key}"

    translation_str = translation_cat.get(key, key)
    if placeholders:
        try:
            translation_str = translation_str.format(**placeholders)
        except KeyError as ex:
            _LOGGER.error(
                "Placeholder %s not found in translation for %s", ex, category
            )

    return translation_str


async def get_coordinator_from_device(
    hass: HomeAssistant, device_id: str
) -> "DiveraCoordinator":
    """Get the DiveraCoordinator instance associated with a given device ID.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        device_id (str): The device ID to look up.

    Returns:
        DiveraCoordinator: The associated DiveraCoordinator instance.

    Raises:
        HomeAssistantError: If the device or coordinator is not found.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device or not device.config_entries:
        raise HomeAssistantError(f"Device not found: {device_id}")

    config_entry_id = next(iter(device.config_entries), None)
    if not config_entry_id:
        raise HomeAssistantError(f"Config entry not found for device: {device_id}")

    entry = hass.config_entries.async_get_entry(config_entry_id)
    if not entry or entry.domain != DOMAIN:
        raise HomeAssistantError(f"Config entry not found for device: {device_id}")

    coordinator = hass.data[DOMAIN][entry.data.get(D_UCR_ID)]["coordinator"]
    if not coordinator:
        raise HomeAssistantError(f"Coordinator not found for device: {device_id}")

    return coordinator
