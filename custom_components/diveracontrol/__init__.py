"""Initializing DiveraControl integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers import entity_registry as er

from .const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_INTEGRATION_VERSION,
    D_UCR_ID,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)
from .coordinator import DiveraCoordinator
from .divera_api import DiveraAPI
from .service import async_register_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.CALENDAR, Platform.DEVICE_TRACKER, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up DiveraControl at Home Assistant start to register services."""
    async_register_services(hass, DOMAIN)
    return True


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
    api_key: str = config_entry.data.get(D_API_KEY) or ""

    _LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, ucr_id)

    try:
        api = DiveraAPI(
            hass,
            ucr_id,
            api_key,
        )
        coordinator = DiveraCoordinator(
            hass,
            api,
            config_entry,
        )

        # create references in config_entry
        # for easy access of coordinator
        config_entry.runtime_data = coordinator
        # hass.data.get(DOMAIN, {}).get(ucr_id, {}).get(D_COORDINATOR)

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN].setdefault(ucr_id, {})[D_COORDINATOR] = coordinator

        await coordinator.async_config_entry_first_refresh()

        config_entry.async_on_unload(api.close)
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        _LOGGER.debug("Setting up cluster %s (%s) succesfully", cluster_name, ucr_id)

    except (TimeoutError, ConnectionError) as err:
        _LOGGER.error("Connection failed: %s", err)
        raise ConfigEntryNotReady("Failed to connect to Divera API") from err
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected error during setup")
        raise ConfigEntryNotReady("Unexpected error during setup") from err

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    cluster_name = config_entry.data.get(D_CLUSTER_NAME)
    ucr_id = config_entry.data.get(D_UCR_ID)

    _LOGGER.debug("Start removing cluster: %s (%s)", cluster_name, ucr_id)

    if not await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        return False

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(ucr_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    _LOGGER.info("Successfully removed cluster %s (%s)", cluster_name, ucr_id)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config_entry to the respective version.

    HA Standard: method will be called if manifest version does not match the config_entry version. So no need to compare versions in coding, just check for the respective version.
    Expect downgrades!

    """

    # changing to v1.2.0
    if VERSION == 1 and MINOR_VERSION == 2:
        _LOGGER.info(
            "Migrating config entry to version %s.%s.%s",
            VERSION,
            MINOR_VERSION,
            PATCH_VERSION,
        )
        if D_INTEGRATION_VERSION not in config_entry.data:
            _LOGGER.info("Adding integration version to existing config entry")

            hass.config_entries.async_update_entry(
                config_entry,
                data={
                    **config_entry.data,
                    D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
                },
                version=VERSION,
                minor_version=MINOR_VERSION,
            )

        ir.async_create_issue(
            hass,
            DOMAIN,
            f"breaking_changes_v1_2_0_{config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="breaking_changes_v1_2_0",
            translation_placeholders={
                "cluster_name": config_entry.data.get(D_CLUSTER_NAME, "Unknown"),
            },
        )

        # Remove all existing entity registry entries that belong to this
        # config entry. This prevents old/unavailable entities from lingering
        # after the upgrade. We do this before the integration creates new
        # entities so the new registration is clean.
        try:
            ent_reg = er.async_get(hass)
            entries = [
                e
                for e in ent_reg.entities.values()
                if e.config_entry_id == config_entry.entry_id
            ]

            for entry in entries:
                _LOGGER.info(
                    "Migration: removing old entity registry entry %s (unique_id=%s)",
                    entry.entity_id,
                    entry.unique_id,
                )
                ent_reg.async_remove(entry.entity_id)

        except Exception:
            _LOGGER.exception(
                "Failed to remove old entity registry entries during migration"
            )
    return True
