"""Initializing DiveraControl integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_UCR_ID,
    DEFAULT_API,
    DEFAULT_COORDINATOR,
    DEFAULT_DEVICE_TRACKER,
    DEFAULT_SENSORS,
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
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
            dict(config_entry.data),
        )

        hass.data.setdefault(DOMAIN, {})[ucr_id] = {
            DEFAULT_COORDINATOR: coordinator,
            DEFAULT_API: api,
            DEFAULT_SENSORS: {},
            DEFAULT_DEVICE_TRACKER: {},
        }

        await coordinator.async_config_entry_first_refresh()

        config_entry.async_on_unload(api.close)
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        # async_register_services(hass, DOMAIN)

        _LOGGER.debug("Setting up cluster %s (%s) succesfully", cluster_name, ucr_id)

    except Exception as err:
        _LOGGER.exception(
            "Error setting up cluster %s (%s), error: %s",
            cluster_name,
            ucr_id,
            err,
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

    if not await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        return False

    if DOMAIN in hass.data and ucr_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(ucr_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    _LOGGER.info("Successfully removed cluster %s (%s)", cluster_name, ucr_id)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config_entry of integration DiveraControl."""
    current_version = config_entry.version
    current_minor = config_entry.minor_version
    current_patch: int = config_entry.patch_version if config_entry.patch_version else 0

    _LOGGER.debug(
        "Migrating configuration from version %s.%s.%s",
        current_version,
        current_minor,
        current_patch,
    )

    if current_version == 0:
        # migration from before v0.9 not supported
        if current_minor < 9:
            _LOGGER.error(
                "Migration from versions older than v0.9 is not supported. "
                "Please delete the integration and re-add it"
            )
            return False

        # migration from v0.9 → v1.0 - no changes needed
        if current_minor >= 9:
            new_data = {**config_entry.data}

            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                version=VERSION,
                minor_version=MINOR_VERSION,
            )

    # migrations from v1.0.0
    elif current_version == 1:
        # from v1.0.0 to v1.2.0 no changes needed
        if current_minor < 2 and MINOR_VERSION < 2:
            hass.config_entries.async_update_entry(
                config_entry,
                data=config_entry.data,
                version=VERSION,
                minor_version=MINOR_VERSION,
            )
            _LOGGER.debug(
                "Migration to version %s.%s.%s completed",
                VERSION,
                MINOR_VERSION,
                PATCH_VERSION,
            )

        # migrations from v1.*.* to v1.2.*
        if current_minor < 2 and MINOR_VERSION >= 2:
            hass.config_entries.async_update_entry(
                config_entry,
                data=config_entry.data,
                version=VERSION,
                minor_version=MINOR_VERSION,
            )
            _LOGGER.warning(
                "Migration to version %s.%s.%s completed"
                "Due to bigger changes in services and actions, please check all your action calls!",
                VERSION,
                MINOR_VERSION,
                PATCH_VERSION,
            )

    return True
