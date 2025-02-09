"""Initializing myDivera integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import DiveraAPI
from .const import D_UCR, DOMAIN, MINOR_VERSION, VERSION
from .coordinator import DiveraCoordinator
from .service import async_register_services

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]
LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up myDivera from a config entry."""
    hub = config_entry.data
    hub_id = hub.get(D_UCR)

    if not hub_id:
        LOGGER.error("Missing hub ID in config entry: %s", config_entry)
        return False

    LOGGER.debug("Setting up hub: %s (%s)", hub.get("name", "Unknown"), hub_id)

    api = DiveraAPI(hass, hub.get("api_key"), hub_id)
    coordinator = DiveraCoordinator(hass, api, hub, hub_id, config_entry.entry_id)

    hass.data.setdefault(DOMAIN, {})[hub_id] = {
        "coordinator": coordinator,
        "sensors": {},
        "api": api,
    }

    try:
        await coordinator.initialize_data()
    except Exception:
        LOGGER.exception(
            "Failed to initialize data for hub %s (%s)",
            hub.get("name", "Unknown"),
            hub_id,
        )
        return False

    try:
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    except Exception:
        LOGGER.exception(
            "Failed to register platforms for hub %s (%s)",
            hub.get("name", "Unknown"),
            hub_id,
        )
        return False

    try:
        await async_register_services(hass, DOMAIN)
    except Exception:
        LOGGER.exception(
            "Failed to register services for hub %s (%s)",
            hub.get("name", "Unknown"),
            hub_id,
        )
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hub = config_entry.data
    hub_id = hub.get(D_UCR)

    if not hub_id:
        LOGGER.error("Missing hub ID during unload: %s", config_entry)
        return False

    LOGGER.info("Unloading hub: %s (%s)", hub.get("name", "Unknown"), hub_id)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok and DOMAIN in hass.data and hub_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][hub_id].get("coordinator")
        if coordinator:
            await coordinator.remove_listeners()

        hass.data[DOMAIN].pop(hub_id, None)
        LOGGER.info(
            "Removed coordinator for hub: %s (%s)", hub.get("name", "Unknown"), hub_id
        )

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
    """Handle automatic creation of a hub configuration from YAML."""
    if any(
        entry.data.get(D_UCR) == import_data[D_UCR]
        for entry in self._async_current_entries()
    ):
        LOGGER.warning("Hub '%s' already configured", import_data[D_UCR])
        return self.async_abort(reason="already_configured")

    LOGGER.info("Creating hub '%s'", import_data["name"])
    return self.async_create_entry(title=import_data["name"], data=import_data)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to new schema."""
    LOGGER.debug(
        "Migrating configuration from version %s.%s",
        entry.version,
        getattr(entry, "minor_version", "N/A"),
    )

    if entry.version != VERSION:
        new_data = (
            entry.data.copy()
        )  # Kopiere die Daten, um Änderungen sicher vorzunehmen

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=VERSION,
            minor_version=MINOR_VERSION,
        )
        LOGGER.info("Migrated config entry to version %s.%s", VERSION, MINOR_VERSION)

    if entry.minor_version != MINOR_VERSION:
        new_data = (
            entry.data.copy()
        )  # Kopiere die Daten, um Änderungen sicher vorzunehmen

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=VERSION,
            minor_version=MINOR_VERSION,
        )
        LOGGER.info("Migrated config entry to version %s.%s", VERSION, MINOR_VERSION)

    return True
