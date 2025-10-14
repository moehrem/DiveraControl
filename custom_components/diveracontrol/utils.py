"""Contain several helper methods for DiveraControl integration."""

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.translation import async_get_translations

from .const import (
    BASE_API_URL,
    D_ACCESS,
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_OPEN_ALARMS,
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

_LOGGER = logging.getLogger(__name__)


def permission_check(
    hass: HomeAssistant,
    ucr_id: str,
    perm_key: str,
) -> None:
    """Check permission and return success.

    Args:
        hass: HomeAssistant instance.
        ucr_id: User cluster relation ID.
        perm_key: Permission key to check.

    Returns:
        True if permission granted, False if denied.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR)
    if not coordinator:
        return

    cluster_data = coordinator.data

    if cluster_data is None:
        raise HomeAssistantError("No permission data available yet, permission denied")

    user_access = cluster_data.get(D_USER, {}).get(D_ACCESS, {})

    # Management permission grants all access
    if user_access.get(PERM_MANAGEMENT):
        _LOGGER.debug(
            "Management permission granted for cluster '%s'",
            coordinator.cluster_name,
        )
        return

    if not user_access.get(perm_key):
        raise HomeAssistantError(
            f"Permission '{perm_key}' denied for cluster '{coordinator.cluster_name}'"
        )

    return


def get_device_info(cluster_name: str) -> DeviceInfo:
    """Return device information, used in sensor and tracker base classes."""
    return {
        "identifiers": {(DOMAIN, cluster_name)},
        "name": cluster_name,
        "manufacturer": MANUFACTURER,
        "model": DOMAIN,
        "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        "entry_type": "service",  # type: ignore[misc]
        "configuration_url": f"{BASE_API_URL}session/login.html",
    }


def _get_coordinator_from_device(hass: HomeAssistant, device_id: str) -> dict[str, Any]:
    """Get coordinator data dictionary for a device.

    Args:
        hass: Home Assistant instance.
        device_id: Device ID.

    Returns:
        Integration data dictionary containing 'api' and 'coordinator'.

    Raises:
        HomeAssistantError: If device or integration data not found.
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
        raise HomeAssistantError(f"Invalid config entry for device: {device_id}")

    # ucr_id = entry.data.get(D_UCR_ID)
    # if not ucr_id:
    #     raise HomeAssistantError(f"UCR ID not found for device: {device_id}")

    # coordinator = hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR)
    # if not coordinator:
    #     raise HomeAssistantError(f"Integration data not found for device: {device_id}")

    coordinator = entry.runtime_data

    return coordinator


def get_coordinator_key_from_device(
    hass: HomeAssistant,
    device_id: str,
    key: str | None = None,
) -> dict[str, Any]:
    """Get the DiveraCoordinator instance for a device.

    Args:
        hass: Home Assistant instance.
        device_id: Device ID to look up.
        key: Key to retrieve from coordinator data.

    Returns:
        The associated DiveraCoordinator instance.

    Raises:
        HomeAssistantError: If device or coordinator is not found.
    """
    coordinator = _get_coordinator_from_device(hass, device_id)

    if not hasattr(coordinator, key):
        raise HomeAssistantError(
            f"Key {key} not found in coordinator for device: {device_id}"
        )

    if key is None:
        return coordinator

    return getattr(coordinator, key)


async def handle_entity(
    hass: HomeAssistant,
    data: dict[str, Any],
    service: str,
    ucr_id: str,
    entity_id: int | str,
) -> None:
    """Update entity data in coordinator after service call.

    Args:
        hass: Home Assistant instance
        data: Service call with data
        service: Service name that was called
        ucr_id: User cluster relation ID
        entity_id: Entity ID to update

    Raises:
        HomeAssistantError: If service is unknown or coordinator not found

    """
    entity_id_str = str(entity_id)
    coordinator = hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR)

    if not coordinator:
        msg = await get_translation(
            hass,
            "exceptions",
            "coordinator_not_found.message",
            {"ucr_id": ucr_id},
        )
        raise HomeAssistantError(msg)

    # Get current coordinator data
    coord_data = coordinator.data.copy()

    match service:
        case "put_alarm" | "post_close_alarm":
            # Update alarm data
            alarm_items = coord_data.get(D_ALARM, {}).get("items", {})
            if entity_id_str not in alarm_items:
                _LOGGER.warning(
                    "Alarm %s not found in coordinator data for service %s",
                    entity_id_str,
                    service,
                )
                return

            alarm_data = alarm_items[entity_id_str]

            # Update only relevant fields from service call
            for key, value in data.items():
                if key in ("device_id", "alarm_id"):
                    continue
                if key in alarm_data:
                    alarm_data[key] = value

        case "post_vehicle_status":
            # Update vehicle FMS status
            vehicle_items = coord_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
            if entity_id_str not in vehicle_items:
                _LOGGER.warning(
                    "Vehicle %s not found in coordinator data for service %s",
                    entity_id_str,
                    service,
                )
                return

            vehicle_data = vehicle_items[entity_id_str]

            # Update other vehicle fields
            for key, value in data.items():
                if key in ("device_id", "vehicle_id", "status", "status_id"):
                    continue
                if key in vehicle_data:
                    vehicle_data[key] = value

        case "post_using_vehicle_property":
            # Update vehicle properties
            vehicle_items = coord_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
            if entity_id_str not in vehicle_items:
                _LOGGER.warning(
                    "Vehicle %s not found in coordinator data for service %s",
                    entity_id_str,
                    service,
                )
                return

            vehicle_data = vehicle_items[entity_id_str]

            # Update properties object
            properties = data.get("properties", {})
            if properties:
                if "properties" not in vehicle_data:
                    vehicle_data["properties"] = {}
                vehicle_data["properties"].update(properties)

        case "post_using_vehicle_crew":
            # Update vehicle crew
            vehicle_items = coord_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
            if entity_id_str not in vehicle_items:
                _LOGGER.warning(
                    "Vehicle %s not found in coordinator data for service %s",
                    entity_id_str,
                    service,
                )
                return

            vehicle_data: dict[str, Any] = vehicle_items[entity_id_str]
            mode: str | None = data.get("mode")
            new_crew: list[int] = data.get("crew", [])

            if "crew" not in vehicle_data:
                vehicle_data["crew"] = []

            # extract IDs for easier handling
            current_crew: set[int] = {item["id"] for item in vehicle_data["crew"]}

            match mode:
                case "add":
                    current_crew.update(new_crew)
                case "remove":
                    current_crew.difference_update(new_crew)
                case "reset":
                    current_crew.clear()
                case _:
                    _LOGGER.warning("Unknown crew mode: %s", mode)

            # convert to Divera format
            vehicle_data["crew"] = [{"id": crew_id} for crew_id in sorted(current_crew)]

        case _:
            # Unknown service
            msg = await get_translation(
                hass,
                "exceptions",
                "unknown_service.message",
                {"service": service},
            )
            _LOGGER.error(msg)
            raise HomeAssistantError(msg)

    # Update coordinator with modified data
    coordinator.async_set_updated_data(coord_data)
    _LOGGER.debug(
        "Updated coordinator data for %s after %s service call",
        entity_id_str,
        service,
    )


def set_update_interval(
    cluster_data: dict[str, Any],
    interval_data: dict[str, Any],
    old_interval: timedelta | None,
) -> timedelta:
    """Set update interval based on open alarms.

    Args:
        cluster_data: Cluster data of coordinator.
        interval_data: Dictionary containing update interval settings.
        old_interval: Previous update interval.

    Returns:
        New update interval.
    """
    # Count open alarms
    alarm_items = cluster_data.get(D_ALARM, {}).get("items", {})
    open_alarms = sum(
        1
        for alarm_details in alarm_items.values()
        if not alarm_details.get("closed", True)
    )

    # Store open alarm count
    cluster_data.setdefault(D_ALARM, {})[D_OPEN_ALARMS] = open_alarms

    # Determine new interval
    new_interval = (
        interval_data[D_UPDATE_INTERVAL_ALARM]
        if open_alarms > 0
        else interval_data[D_UPDATE_INTERVAL_DATA]
    )

    # Log only if interval changed
    if old_interval != new_interval:
        _LOGGER.debug(
            "Update interval changed to %s for unit '%s' (open alarms: %d)",
            new_interval,
            cluster_data.get(D_CLUSTER_NAME, "Unknown"),
            open_alarms,
        )

    return new_interval


async def get_translation(
    hass: HomeAssistant,
    category: str,
    key: str,
    placeholders: dict[str, Any] | None = None,
) -> str:
    """Get translated message.

    Args:
        hass: Home Assistant instance.
        category: Translation category to look up.
        key: Translation key to look up.
        placeholders: Optional placeholders for formatting.

    Returns:
        The translated string, formatted with placeholders if provided.
    """
    translations = await async_get_translations(
        hass, hass.config.language, category, {DOMAIN}
    )

    translation_key = f"component.{DOMAIN}.{category}.{key}"
    translation_str = translations.get(translation_key, translation_key)

    if placeholders:
        try:
            translation_str = translation_str.format(**placeholders)
        except KeyError as ex:
            _LOGGER.error(
                "Missing placeholder '%s' in translation for key '%s'",
                ex,
                translation_key,
            )

    return translation_str
