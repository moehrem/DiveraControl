"""Contain several helper methods for DiveraControl integration."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.translation import async_get_translations

from .const import D_CLUSTER_ID, D_COORDINATOR, D_RELATIONS_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_ucr_data_from_device(
    hass: HomeAssistant,
    device_id: str,
    key: str | None = None,
) -> Any:
    """Get ucr data of coordinator for a device.

    Args:
        hass: Home Assistant instance.
        device_id: Device ID to look up.
        key: Key to retrieve from coordinator data.

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

    # Get ucr_id from device identifiers
    ucr_id = next(
        (ident for dom, ident in device.identifiers if dom == DOMAIN),
        None,
    )
    if not ucr_id:
        raise HomeAssistantError(
            f"UCR ID not found in device identifiers for device: {device_id}"
        )

    # Get coordinator
    coordinator = (
        hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR, {}).get(ucr_id)
    )

    if coordinator is None:
        raise HomeAssistantError(f"Coordinator not found for device: {device_id}")

    if key is None:
        return coordinator

    if not hasattr(coordinator, key):
        raise HomeAssistantError(
            f"Key '{key}' not found in coordinator for device: {device_id}"
        )
    return getattr(coordinator, key)


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


def get_cluster_coordinators_ucrs_from_config_hass(
    config_data: dict[str, Any], hass: HomeAssistant
) -> tuple[str, dict[str, Any], list[Any]]:
    """Get cluster_id, coordinators and UCR data from config entry.

    Args:
        config_data: Config entry data.
        hass: Home Assistant instance.

    Returns:
        Tuple containing cluster_id, coordinators dict and list of DiveraCoordinators.

    """

    cluster_id = config_data.get(D_CLUSTER_ID)
    coordinators = hass.data.get(DOMAIN, {}).get(cluster_id, {}).get(D_COORDINATOR)
    ucrs = config_data.get(D_RELATIONS_KEY)

    return cluster_id, coordinators, ucrs
