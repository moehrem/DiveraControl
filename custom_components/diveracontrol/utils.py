"""Contain several helper methods for DiveraControl integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.translation import async_get_translations

from .const import (
    D_ALARM,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_OPEN_ALARMS,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_ucr_data_from_device(
    hass: HomeAssistant,
    device_id: str,
    key: str | None = None,
    ucr_id: str | None = None,
) -> Any:
    """Get ucr data of coordinator for a device.

    Args:
        hass: Home Assistant instance.
        device_id: Device ID to look up.
        key: Key to retrieve from coordinator data.
        ucr_id: Optional explicit user-cluster-relation id.

    Returns:
        The associated ucr data of the coordinator.

    Raises:
        HomeAssistantError: If device or coordinator is not found.
    """
    # Get device from registry
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device or not device.config_entries:
        raise HomeAssistantError(
            f"Device not found or has no config entries: {device_id}"
        )

    # Get config entry
    config_entry_id = next(iter(device.config_entries), None)
    if not config_entry_id:
        raise HomeAssistantError(f"Config entry not found for device: {device_id}")

    entry = hass.config_entries.async_get_entry(config_entry_id)
    if not entry or entry.domain != DOMAIN:
        raise HomeAssistantError(f"Invalid config entry for device: {device_id}")

    # Get cluster_id
    cluster_id = entry.data.get(D_CLUSTER_ID)
    if not cluster_id:
        raise HomeAssistantError(
            f"Cluster ID not found in config entry for device: {device_id}"
        )

    # Get ucr_id from explicit argument or from device identifiers.
    resolved_ucr_id = ucr_id or next(
        (ident for dom, ident in device.identifiers if dom == DOMAIN),
        None,
    )

    coordinators = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR, {})

    if not resolved_ucr_id or resolved_ucr_id == cluster_id:
        # Cluster-based devices do not encode a specific user relation.
        # Pick a deterministic fallback so device actions/services can still run.
        if not coordinators:
            raise HomeAssistantError(f"No coordinators found for device: {device_id}")
        resolved_ucr_id = sorted(coordinators)[0]
        _LOGGER.debug(
            "No explicit ucr_id for device %s; using fallback ucr_id %s",
            device_id,
            resolved_ucr_id,
        )

    # Get coordinator
    coordinator = coordinators.get(resolved_ucr_id)

    if coordinator is None:
        raise HomeAssistantError(f"Coordinator not found for device: {device_id}")

    if key is None:
        return coordinator

    if not hasattr(coordinator, key):
        raise HomeAssistantError(
            f"Key '{key}' not found in coordinator for device: {device_id}"
        )
    return getattr(coordinator, key)


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
    open_alarms = cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)

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
