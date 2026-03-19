"""Initializing DiveraControl integration."""

import logging

import aiohttp
from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    issue_registry as ir,
)

from .const import (
    BASE_API_URL,
    D_API_KEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_INTEGRATION_VERSION,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_USE_WEBHOOKS,
    D_USERGROUP_ID,
    D_WEBHOOK_ID,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)
from .coordinator import DiveraCoordinator
from .divera_api import DiveraAPI, async_get_clientsession
from .log_handler import (
    async_remove_diveracontrol_log_handler,
    async_setup_diveracontrol_log_handler,
)
from .service import async_register_services
from .webhook import async_handle_webhook

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.CALENDAR, Platform.DEVICE_TRACKER, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up DiveraControl at Home Assistant start to register services."""
    async_setup_diveracontrol_log_handler(hass)
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
    cluster_id: str = config_entry.data.get(D_CLUSTER_ID) or ""
    cluster_name: str = config_entry.data.get(D_CLUSTER_NAME) or ""
    base_url: str = config_entry.data.get(D_BASE_API_URL) or ""
    use_webhooks: bool = config_entry.data.get(D_USE_WEBHOOKS, False)
    webhook_id: str = config_entry.data.get(D_WEBHOOK_ID) or ""
    relations: dict[str, dict[str, str]] = config_entry.data.get(D_RELATIONS_KEY, {})

    _LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, cluster_id)
    async_setup_diveracontrol_log_handler(hass)

    if not relations:
        raise ConfigEntryNotReady("No user relations configured")

    coordinators_by_ucr: dict[str, DiveraCoordinator] = {}
    apis_by_ucr: dict[str, DiveraAPI] = {}

    # Create API and coordinator instances per user relation.
    for relation in relations.values():
        ucr_id = relation.get(D_UCR_ID)
        api_key = relation.get(D_API_KEY)

        if not ucr_id or not api_key:
            _LOGGER.warning(
                "Skipping invalid user relation in cluster %s (missing ucr_id/api_key)",
                cluster_id,
            )
            continue

        try:
            api = DiveraAPI(
                hass,
                ucr_id,
                api_key,
                base_url,
            )

            coordinator = DiveraCoordinator(
                hass,
                api,
                ucr_id,
                config_entry,
            )

            await coordinator.async_config_entry_first_refresh()
            coordinators_by_ucr[ucr_id] = coordinator
            apis_by_ucr[ucr_id] = api
            config_entry.async_on_unload(api.close)

        except (TimeoutError, ConnectionError) as err:
            await api.close()
            _LOGGER.error(
                "Connection failed for user %s: %s (%s)",
                ucr_id,
                err,
                cluster_name,
            )
            continue
        except ConfigEntryAuthFailed as err:
            await api.close()
            _LOGGER.error(
                "Authentication failed for user %s: %s (%s)",
                ucr_id,
                err,
                cluster_name,
            )
            continue
        except Exception:
            await api.close()
            _LOGGER.exception(
                "Unexpected error during setup for user %s (%s)",
                ucr_id,
                cluster_name,
            )
            continue

    if not coordinators_by_ucr:
        raise ConfigEntryNotReady("Failed to set up any user for this cluster")

    # Keep backward compatibility with existing platform code that expects
    # a single coordinator in runtime_data.
    primary_ucr_id = next(iter(coordinators_by_ucr))
    config_entry.runtime_data = coordinators_by_ucr[primary_ucr_id]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][cluster_id] = {
        D_COORDINATOR: coordinators_by_ucr,
        "apis": apis_by_ucr,
        "primary_ucr_id": primary_ucr_id,
    }

    if use_webhooks and webhook_id:
        async_register(
            hass,
            DOMAIN,
            f"DiveraControl {cluster_name}",
            webhook_id,
            async_handle_webhook,
        )
        config_entry.async_on_unload(lambda: async_unregister(hass, webhook_id))

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    _LOGGER.debug(
        "Setting up cluster %s (%s users) successfully",
        cluster_name,
        len(coordinators_by_ucr),
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    cluster_name = config_entry.data.get(D_CLUSTER_NAME)
    cluster_id = config_entry.data.get(D_CLUSTER_ID)
    use_webhooks: bool = config_entry.data.get(D_USE_WEBHOOKS, False)
    webhook_id: str = config_entry.data.get(D_WEBHOOK_ID) or ""

    _LOGGER.debug("Start removing cluster: %s (%s)", cluster_name, cluster_id)

    if not await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        return False

    if use_webhooks and webhook_id:
        async_unregister(hass, webhook_id)

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(cluster_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
            async_remove_diveracontrol_log_handler(hass)

    _LOGGER.info("Successfully removed cluster %s (%s)", cluster_name, cluster_id)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config_entry to the respective version.

    Note: config_entry.version and config_entry.minor_version are the CONFIG ENTRY
    SCHEMA version numbers. They must be explicitly set during migration to match
    the versions defined in ConfigFlow (VERSION and MINOR_VERSION).

    """

    updated_data = {**config_entry.data}
    migrated = False

    current_version = config_entry.version
    current_minor_version = config_entry.minor_version
    current_patch_version = (
        config_entry.data.get(D_INTEGRATION_VERSION, "0.0.0").split(".")[2]
        or PATCH_VERSION
        or 0
    )

    _LOGGER.info(
        "Installed version: %s.%s.%s, new version: %s.%s.%s, starting migration",
        current_version,
        current_minor_version,
        current_patch_version,
        VERSION,
        MINOR_VERSION,
        PATCH_VERSION or 0,
    )

    # changing to v1.2.0
    # add new integration_version parameter to config entry and create issue for breaking changes
    if current_version == 1 and current_minor_version < 2:
        _LOGGER.info(
            "Migrating config entry to integration version 1.2.0",
        )
        if D_INTEGRATION_VERSION not in updated_data:
            _LOGGER.info("Adding integration version to existing config entry")
            updated_data[D_INTEGRATION_VERSION] = (
                f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
            )

            # set versions to ensure future migrations are correctly applied
            current_version = 1
            current_minor_version = 2
            migrated = True

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

    # changing to v1.3.0
    # add new base_url parameter to config entry

    if current_version == 1 and current_minor_version < 3:
        _LOGGER.info(
            "Migrating config entry to integration version 1.3.0",
        )

        if D_BASE_API_URL not in updated_data:
            _LOGGER.info("Adding base_url to existing config entry")
            updated_data[D_BASE_API_URL] = BASE_API_URL
            updated_data[D_INTEGRATION_VERSION] = (
                f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
            )

            # set versions to ensure future migrations are correctly applied
            current_version = 1
            current_minor_version = 3
            migrated = True

    # changing to v1.4.0
    # add new use_webhooks parameter to config entry
    if current_version == 1 and current_minor_version < 4:
        _LOGGER.info(
            "Migrating config entry to integration version 1.4.0",
        )

        if D_USE_WEBHOOKS not in updated_data:
            _LOGGER.info("Adding use_webhooks to existing config entry")
            updated_data[D_USE_WEBHOOKS] = False
            updated_data[D_INTEGRATION_VERSION] = (
                f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
            )

            # set versions to ensure future migrations are correctly applied
            current_version = 1
            current_minor_version = 4
            migrated = True

    # changing to v2.0.0
    # breaking change: new config entry schema with multiple user relations per cluster
    # but no need to check for multiple users as this was not supported before and thus cannot exist in old config entries
    if current_version == 1 and current_minor_version < 5:
        _LOGGER.info(
            "Migrating config entry to integration version 2.0.0",
        )

        ### OLD config_entry.data STRUCTURE ***
        # str(ucr_id): {
        #     D_UCR_ID: cluster_data[D_UCR_ID],
        #     D_CLUSTER_NAME: cluster_data[D_CLUSTER_NAME],
        #     D_API_KEY: cluster_data[D_API_KEY],
        #     D_BASE_API_URL: _base_api_url,
        #     D_UPDATE_INTERVAL_DATA: _update_interval_data,
        #     D_UPDATE_INTERVAL_ALARM: _update_interval_alarm,
        #     D_USE_WEBHOOKS: _use_webhooks,
        #     D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",

        ### NEW config_entry.data STRUCTURE ***
        # clusters[cluster_id] = {
        #     D_CLUSTER_ID: cluster_id,
        #     D_CLUSTER_NAME: data.get(D_NAME, ""),
        #     D_BASE_API_URL: base_api_url,
        #     D_UPDATE_INTERVAL_DATA: None,  # set later in config flow
        #     D_UPDATE_INTERVAL_ALARM: None,  # set later in config flow
        #     D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        #     D_USE_WEBHOOKS: None,  # set later in config flow
        #     D_RELATIONS_KEY: {
        #         ucr: {
        #             D_UCR_ID: ucr,
        #             D_API_KEY: api_key,
        #             D_USERGROUP_ID: data.get(D_USERGROUP_ID, ""),
        #         },
        #     },
        # }

        # TODO
        # call "validate_api_key" to mimic a regular config flow by api-key
        # read new/missing data
        # transform old single user relation structure into new multi user relation structure

        from .divera_api import DiveraConfigFlowAPI

        session: aiohttp.ClientSession | None = None
        session = async_get_clientsession(hass)
        user_input = {
            D_API_KEY: config_entry.data.get(D_API_KEY, ""),
        }
        base_api_url = config_entry.data.get(D_BASE_API_URL, BASE_API_URL)

        validation_errors, clusters = await DiveraConfigFlowAPI.validate_api_key(
            session,
            user_input,
            base_api_url,
        )

        if validation_errors:
            _LOGGER.error(
                "API key validation failed during migration: %s",
                validation_errors,
            )
            ir.async_create_issue(
                hass,
                DOMAIN,
                f"migration_failed_v2_0_0_{config_entry.entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="migration_failed_v2_0_0",
                translation_placeholders={
                    "cluster_name": config_entry.data.get(D_CLUSTER_NAME, "Unknown"),
                },
            )
            migrated = False
            return False

        # read correct cluster from clusters by matching ucr_id (there should be only one user relation in old config entries, so we can just take the first one)
        ucr_id = config_entry.data.get(D_UCR_ID, "")
        migrated_cluster = next(
            (c for c in clusters.values() if c.get(D_RELATIONS_KEY, {}).get(ucr_id)),
            None,
        )

        # set missing parameters
        migrated_cluster[D_UPDATE_INTERVAL_ALARM] = config_entry.data.get(
            D_UPDATE_INTERVAL_ALARM, 30
        )
        migrated_cluster[D_UPDATE_INTERVAL_DATA] = config_entry.data.get(
            D_UPDATE_INTERVAL_DATA, 60
        )
        migrated_cluster[D_USE_WEBHOOKS] = config_entry.data.get(D_USE_WEBHOOKS, False)

        updated_data = migrated_cluster
        # set versions to ensure future migrations are correctly applied
        current_version = 2
        current_minor_version = 0
        migrated = True

        ir.async_create_issue(
            hass,
            DOMAIN,
            f"breaking_changes_v2_0_0_{config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="breaking_changes_v2_0_0",
            translation_placeholders={
                "cluster_name": config_entry.data.get(D_CLUSTER_NAME, "Unknown"),
            },
        )

    ##### ALWAYS THE ONE AND ONLY FINAL BLOCK #####
    # finalize migration by updating config entry version if any migration step was performed
    if migrated or current_version != VERSION or current_minor_version != MINOR_VERSION:
        hass.config_entries.async_update_entry(
            config_entry,
            data=updated_data,
            version=current_version,
            minor_version=current_minor_version,
        )

    _LOGGER.debug(
        "Migration complete, config_entry is now at version %s.%s.%s",
        current_version,
        current_minor_version,
        PATCH_VERSION,
    )

    return True
