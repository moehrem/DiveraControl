"""Initializing DiveraControl integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed

from .const import (
    D_API_KEY,
    D_CLUSTER_NAME,
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
    config_entry.patch_version = PATCH_VERSION

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN].setdefault(ucr_id, {})

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
    """Migrate old config_entry of integration DiveraControl."""
    current_version = config_entry.version
    current_minor = config_entry.minor_version
    current_patch: int = (
        config_entry.patch_version
        if hasattr(config_entry, "patch_version") and config_entry.patch_version
        else 0
    )

    _LOGGER.debug(
        "Migrating configuration from version %s.%s.%s to %s.%s.%s",
        current_version,
        current_minor,
        current_patch,
        VERSION,
        MINOR_VERSION,
        PATCH_VERSION,
    )

    # Migration from version 0.x
    if current_version == 0:
        if current_minor < 9:
            # Versions before v0.9 are not supported
            _LOGGER.error(
                "Migration from version 0.%s is not supported. "
                "Please delete the integration and re-add it",
                current_minor,
            )
            return False

        # Migration from v0.9+ → current version
        # No data changes needed, just update version
        hass.config_entries.async_update_entry(
            config_entry,
            data={**config_entry.data},
            version=VERSION,
            minor_version=MINOR_VERSION,
        )
        _LOGGER.info(
            "Migration from version 0.%s to %s.%s completed successfully",
            current_minor,
            VERSION,
            MINOR_VERSION,
        )

    # Migration from version 1.x
    elif current_version == 1:
        # Check if migration to v1.2+ (breaking changes in services)
        if current_minor < 2 and MINOR_VERSION >= 2:
            _LOGGER.warning(
                "Migration from version 1.%s.%s to %s.%s.%s includes breaking changes. "
                "Please check all your service and action calls!",
                current_minor,
                current_patch,
                VERSION,
                MINOR_VERSION,
                PATCH_VERSION,
            )

        # Update to current version (no data changes needed)
        hass.config_entries.async_update_entry(
            config_entry,
            data=config_entry.data,
            version=VERSION,
            minor_version=MINOR_VERSION,
        )
        _LOGGER.info(
            "Migration from version 1.%s to %s.%s completed successfully",
            current_minor,
            VERSION,
            MINOR_VERSION,
        )

    # Already at current version or newer
    else:
        _LOGGER.debug(
            "No migration needed - already at version %s.%s",
            current_version,
            current_minor,
        )

    return True
