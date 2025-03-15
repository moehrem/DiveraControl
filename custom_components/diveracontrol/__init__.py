"""Initializing myDivera integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import DiveraAPI
from .const import DOMAIN, D_API_KEY, D_CLUSTER_ID
from .coordinator import DiveraCoordinator
from .service import async_register_services

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.CALENDAR]
LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up DiveraControl from a config entry."""
    cluster = config_entry.data
    cluster_id = cluster.get(D_CLUSTER_ID)
    api_key = cluster.get(D_API_KEY)

    if not cluster_id:
        LOGGER.error("Missing cluster ID in config entry: %s", config_entry)
        return False

    LOGGER.debug(
        "Setting up cluster: %s (%s)", cluster.get("name", "Unknown"), cluster_id
    )

    api = DiveraAPI(hass, cluster_id, api_key)
    coordinator = DiveraCoordinator(hass, api, cluster, cluster_id)

    hass.data.setdefault(DOMAIN, {})[cluster_id] = {
        "coordinator": coordinator,
        "api": api,
        "sensors": {},
        "device_tracker": {},
    }

    try:
        await coordinator.init_cluster_data()
    except Exception:
        LOGGER.exception(
            "Failed to initialize data for cluster %s (%s)",
            cluster.get("name", "Unknown"),
            cluster_id,
        )
        return False

    try:
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    except Exception:
        LOGGER.exception(
            "Failed to register platforms for cluster %s (%s)",
            cluster.get("name", "Unknown"),
            cluster_id,
        )
        return False

    try:
        await async_register_services(hass, DOMAIN)
    except Exception:
        LOGGER.exception(
            "Failed to register services for cluster %s (%s)",
            cluster.get("name", "Unknown"),
            cluster_id,
        )
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    cluster = config_entry.data
    hub_id = cluster.get(D_CLUSTER_ID)

    if not hub_id:
        LOGGER.error("Missing cluster ID during unload: %s", config_entry)
        return False

    LOGGER.debug(
        "Unloading cluster: %s (%s)", cluster.get("cluster_name", "Unknown"), hub_id
    )

    api: DiveraAPI = hass.data[DOMAIN].pop(config_entry.entry_id, None)
    if api:
        await api.close()

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok and DOMAIN in hass.data and hub_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][hub_id].get("coordinator")
        if coordinator:
            await coordinator.remove_listeners()

        hass.data[DOMAIN].pop(hub_id, None)
        LOGGER.info(
            "Removed unit: %s (%s)",
            cluster.get("cluster_name", "Unknown"),
            hub_id,
        )

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok
