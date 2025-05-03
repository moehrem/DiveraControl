"""Initializing DiveraControl integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_UCR_ID,
    DEFAULT_API,
    DEFAULT_COORDINATOR,
    DEFAULT_DEVICE_TRACKER,
    DEFAULT_SENSORS,
    DOMAIN,
)
from .coordinator import DiveraCoordinator
from .divera_api import DiveraAPI
from .service import async_register_services

PLATFORMS = [Platform.CALENDAR, Platform.DEVICE_TRACKER, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up DiveraControl from a config entry.

    Args:
        hass: Home Assistance instance.
        config_entry: DiveraControl config entry.

    Returns:
        bool: True if setup succesfully, otherwise False.

    """
    ucr_id: str = config_entry.data.get(D_UCR_ID) or ""
    cluster_name: str = config_entry.data.get(D_CLUSTER_NAME) or ""
    cluster_api_key: str = config_entry.data.get(D_API_KEY) or ""

    _LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, ucr_id)

    try:
        api = DiveraAPI(
            hass,
            ucr_id,
            cluster_api_key,
        )
        coordinator = DiveraCoordinator(
            hass,
            api,
            dict(config_entry.data),
        )

        hass.data.setdefault(DOMAIN, {})[ucr_id] = {
            DEFAULT_COORDINATOR: coordinator,
            DEFAULT_API: api,
            DEFAULT_SENSORS: {},
            DEFAULT_DEVICE_TRACKER: {},
        }

        await coordinator.async_config_entry_first_refresh()
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
        async_register_services(hass, DOMAIN)

        _LOGGER.debug("Setting up cluster %s (%s) succesfully", cluster_name, ucr_id)

    except Exception:
        _LOGGER.exception(
            "Error setting up cluster %s (%s), error:",
            cluster_name,
            ucr_id,
        )
        return False

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistance instance.
        config_entry: DiveraControl config entry to remove.

    Returns:
        bool: True, if successfully unloaded, otherwise False.

    """
    cluster_name = config_entry.data.get(D_CLUSTER_NAME)
    ucr_id = config_entry.data.get(D_UCR_ID)

    _LOGGER.debug("Start removing cluster: %s (%s)", cluster_name, ucr_id)

    try:
        api: DiveraAPI = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if api:
            await api.close()

        if not await hass.config_entries.async_unload_platforms(
            config_entry, PLATFORMS
        ):
            return False

        if DOMAIN in hass.data and ucr_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][ucr_id].get(D_COORDINATOR)
            if coordinator:
                await coordinator.remove_listeners()

            hass.data[DOMAIN].pop(ucr_id, None)
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)

            _LOGGER.info(
                "Successfully removed cluster %s (%s)",
                cluster_name,
                ucr_id,
            )

    except Exception:
        _LOGGER.exception(
            "Error removing cluster %s (%s), error:",
            cluster_name,
            ucr_id,
        )
        return False

    return True
