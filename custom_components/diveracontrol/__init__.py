"""Initializing myDivera integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import DiveraAPI
from .const import D_API_KEY, D_CLUSTER_ID, D_CLUSTER_NAME, D_COORDINATOR, DOMAIN
from .coordinator import DiveraCoordinator
from .service import async_register_services

PLATFORMS = [Platform.CALENDAR, Platform.DEVICE_TRACKER, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up DiveraControl from a config entry.

    Args:
        hass: Home Assistance instance.
        config_entry: DiveraControl config entry.

    Returns:
        bool: True if setup succesfully, otherwise False.

    """
    cluster_config_data = config_entry.data
    cluster_id = cluster_config_data.get(D_CLUSTER_ID)
    cluster_name = cluster_config_data.get(D_CLUSTER_NAME)
    cluster_api_key = cluster_config_data.get(D_API_KEY)

    _LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, cluster_id)

    try:
        api = DiveraAPI(hass, cluster_id, cluster_api_key)
        coordinator = DiveraCoordinator(hass, api, cluster_config_data, cluster_id)

        hass.data.setdefault(DOMAIN, {})[cluster_id] = {
            "coordinator": coordinator,
            "api": api,
            "sensors": {},
            "device_tracker": {},
        }

        await coordinator.async_config_entry_first_refresh()
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
        await async_register_services(hass, DOMAIN)

        _LOGGER.debug(
            "Setting up cluster %s (%s) succesfully", cluster_name, cluster_id
        )

    except Exception as err:
        _LOGGER.exception(
            "Error setting up cluster %s (%s), error: %s",
            cluster_name,
            cluster_id,
            err,
        )
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistance instance.
        config_entry: DiveraControl config entry to remove.

    Returns:
        bool: True, if successfully unloaded, otherwise False.

    """
    cluster_name = config_entry.data.get(D_CLUSTER_NAME)
    cluster_id = config_entry.data.get(D_CLUSTER_ID)

    _LOGGER.debug("Start removing cluster: %s (%s)", cluster_name, cluster_id)

    try:
        api: DiveraAPI = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if api:
            await api.close()

        if not await hass.config_entries.async_unload_platforms(
            config_entry, PLATFORMS
        ):
            return False

        if DOMAIN in hass.data and cluster_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][cluster_id].get(D_COORDINATOR)
            if coordinator:
                await coordinator.remove_listeners()

            hass.data[DOMAIN].pop(cluster_id, None)
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)

            _LOGGER.info(
                "Successfully removed cluster %s (%s)",
                cluster_name,
                cluster_id,
            )

    except Exception as err:
        _LOGGER.exception(
            "Error removing cluster %s (%s), error: %s",
            cluster_name,
            cluster_id,
            err,
        )
        return False

    return True
