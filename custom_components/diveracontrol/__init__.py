"""Initializing myDivera integration."""

import logging

from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import DiveraAPI
from .const import DOMAIN, D_API_KEY, D_CLUSTER_ID, D_CLUSTER_NAME
from .coordinator import DiveraCoordinator
from .service import async_register_services

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.CALENDAR]
LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up DiveraControl from a config entry."""
    cluster_config_data = config_entry.data
    cluster_id = cluster_config_data.get(D_CLUSTER_ID)
    cluster_name = cluster_config_data.get(D_CLUSTER_NAME)
    cluster_api_key = cluster_config_data.get(D_API_KEY)

    if not cluster_id:
        LOGGER.error("Missing cluster ID in config entry: %s", config_entry)
        return False

    LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, cluster_id)

    api = DiveraAPI(hass, cluster_id, cluster_api_key)
    coordinator = DiveraCoordinator(hass, api, cluster_config_data, cluster_id)

    hass.data.setdefault(DOMAIN, {})[cluster_id] = {
        "coordinator": coordinator,
        "api": api,
        "sensors": {},
        "device_tracker": {},
    }

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        LOGGER.exception(
            "Failed to initialize data for cluster %s (%s)",
            cluster_name,
            cluster_id,
        )
        return False

    try:
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    except Exception:
        LOGGER.exception(
            "Failed to register platforms for cluster %s (%s)",
            cluster_name,
            cluster_id,
        )
        return False

    try:
        await async_register_services(hass, DOMAIN)
    except Exception:
        LOGGER.exception(
            "Failed to register services for cluster %s (%s)",
            cluster_name,
            cluster_id,
        )
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    cluster_id = config_entry.data.get(D_CLUSTER_ID)
    cluster_name = config_entry.data.get(D_CLUSTER_NAME)

    if not cluster_id:
        LOGGER.error("Missing cluster ID during unload: %s", config_entry)
        return False

    LOGGER.debug("Unloading cluster: %s (%s)", cluster_name, cluster_id)

    api: DiveraAPI = hass.data[DOMAIN].pop(config_entry.entry_id, None)
    if api:
        await api.close()

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok and DOMAIN in hass.data and cluster_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][cluster_id].get("coordinator")
        if coordinator:
            await coordinator.remove_listeners()

        hass.data[DOMAIN].pop(cluster_id, None)
        LOGGER.info(
            "Removed unit: %s (%s)",
            cluster_name,
            cluster_id,
        )

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok
