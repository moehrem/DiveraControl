"""Initializing DiveraControl integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
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
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USE_WEBHOOKS,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)
from .coordinator import DiveraCoordinator
from .divera_api import DiveraConfigFlowAPI
from .log_handler import (
    async_remove_diveracontrol_log_handler,
    async_setup_diveracontrol_log_handler,
)
from .service import async_register_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [
    Platform.CALENDAR,
    Platform.DEVICE_TRACKER,
    Platform.SELECT,
    Platform.SENSOR,
]
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

    _LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, cluster_id)
    async_setup_diveracontrol_log_handler(hass)

    relations = config_entry.data.get(D_RELATIONS_KEY, {})
    if not isinstance(relations, dict):
        relations = {}

    # Flatten legacy subentries into D_RELATIONS_KEY and remove subentries to
    # avoid an extra "user" layer in the integration UI.
    if config_entry.subentries:
        merged_relations = {
            str(ucr): dict(data)
            for ucr, data in relations.items()
            if isinstance(data, dict)
        }
        for subentry in config_entry.subentries.values():
            ucr_id = str(subentry.unique_id or subentry.data.get(D_UCR_ID, ""))
            if not ucr_id:
                continue
            relation_data = dict(subentry.data)
            relation_data[D_UCR_ID] = relation_data.get(D_UCR_ID, ucr_id)
            merged_relations[ucr_id] = relation_data

        hass.config_entries.async_update_entry(
            config_entry,
            data={
                **config_entry.data,
                D_RELATIONS_KEY: merged_relations,
            },
        )
        for subentry_id in list(config_entry.subentries):
            hass.config_entries.async_remove_subentry(config_entry, subentry_id)

        relations = merged_relations

    coordinators_by_ucr: dict[str, DiveraCoordinator] = {}

    # Create coordinator instances per user relation.
    for raw_ucr_id in relations:
        ucr_id = str(raw_ucr_id)
        if not ucr_id:
            continue

        try:
            coordinator = DiveraCoordinator(
                hass,
                config_entry,
                ucr_id,
            )

            await coordinator.async_config_entry_first_refresh()
            coordinators_by_ucr[ucr_id] = coordinator

        except (TimeoutError, ConnectionError) as err:
            _LOGGER.error(
                "Connection failed for user %s: %s (%s)",
                ucr_id,
                err,
                cluster_name,
            )
            continue
        except ConfigEntryAuthFailed as err:
            _LOGGER.error(
                "Authentication failed for user %s: %s (%s)",
                ucr_id,
                err,
                cluster_name,
            )
            continue
        except Exception:
            _LOGGER.exception(
                "Unexpected error during setup for user %s (%s)",
                ucr_id,
                cluster_name,
            )
            continue

    if not coordinators_by_ucr:
        raise ConfigEntryNotReady("Failed to set up any user for this cluster")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][cluster_id] = {
        D_COORDINATOR: coordinators_by_ucr,
    }

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

    _LOGGER.debug("Start removing cluster: %s (%s)", cluster_name, cluster_id)

    if not await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        return False

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(cluster_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
            async_remove_diveracontrol_log_handler(hass)

    _LOGGER.info("Successfully removed cluster %s (%s)", cluster_name, cluster_id)
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Remove a user device from a cluster config entry.

    Home Assistant calls this when the user clicks "Delete device" in the UI.
    We remove the matching UCR relation from D_RELATIONS_KEY and reload the
    entry so related entities are cleaned up and not recreated.
    """

    ucr_id: str | None = next(
        (
            identifier
            for domain, identifier in device_entry.identifiers
            if domain == DOMAIN
        ),
        None,
    )
    if ucr_id is None:
        return False

    if ucr_id == str(config_entry.data.get(D_CLUSTER_ID, "")):
        return False

    relations = config_entry.data.get(D_RELATIONS_KEY, {})
    if not isinstance(relations, dict):
        return False

    if ucr_id not in relations:
        return False

    # Keep at least one relation in the entry; removing the last one would
    # leave an invalid cluster config entry.
    if len(relations) <= 1:
        _LOGGER.warning(
            "Cannot remove last user relation %s from cluster %s",
            ucr_id,
            config_entry.data.get(D_CLUSTER_ID, "unknown"),
        )
        return False

    updated_relations = dict(relations)
    updated_relations.pop(ucr_id, None)
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            **config_entry.data,
            D_RELATIONS_KEY: updated_relations,
        },
    )
    await hass.config_entries.async_reload(config_entry.entry_id)

    _LOGGER.info(
        "Removed user relation %s from cluster %s via device deletion",
        ucr_id,
        config_entry.data.get(D_CLUSTER_ID, "unknown"),
    )
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config_entry to the respective version.

    Note: config_entry.version and config_entry.minor_version are the CONFIG ENTRY
    SCHEMA version numbers. They must be explicitly set during migration to match
    the versions defined in ConfigFlow (VERSION and MINOR_VERSION).

    """

    updated_data = {**config_entry.data}
    clear_registry_entries = False
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
    # user_cluster_relations are stored in D_RELATIONS_KEY inside config entry data
    # but no need to check for multiple users as this was not supported before and thus cannot exist in old config entries
    if current_version == 1 and current_minor_version < 5:
        _LOGGER.info(
            "Migrating config entry to integration version 2.0.0",
        )

        user_input = {
            D_API_KEY: config_entry.data.get(D_API_KEY, ""),
        }
        base_api_url = config_entry.data.get(D_BASE_API_URL, BASE_API_URL)

        config_api = DiveraConfigFlowAPI(hass, base_api_url)
        validation_errors, clusters = await config_api.request_access(user_input)

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

        # read correct cluster from clusters by matching ucr_id (there is only one user relation in old config entries, so we can just take the first one)
        ucr_id = config_entry.data.get(D_UCR_ID, "")
        migrated_cluster = next(
            (c for c in clusters.values() if c.get(D_RELATIONS_KEY, {}).get(ucr_id)),
            None,
        )

        if migrated_cluster is None:
            _LOGGER.error(
                "Migration failed: no cluster mapping found for ucr_id %s in entry %s",
                ucr_id,
                config_entry.entry_id,
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
            return False

        # Normalize relation data and keep it in config entry data.
        raw_relations = migrated_cluster.pop(D_RELATIONS_KEY, {})
        relations: dict[str, dict] = {}
        for raw_ucr_id, raw_relation_data in raw_relations.items():
            if not isinstance(raw_relation_data, dict):
                continue

            ucr_id = str(raw_ucr_id)
            relation_data = dict(raw_relation_data)
            relation_data.pop(D_BASE_API_URL, None)
            relation_data.pop(D_UPDATE_INTERVAL_DATA, None)
            relation_data.pop(D_UPDATE_INTERVAL_ALARM, None)
            relation_data[D_UCR_ID] = relation_data.get(D_UCR_ID, ucr_id)
            relations[ucr_id] = relation_data

        updated_data = {
            **migrated_cluster,
            D_UPDATE_INTERVAL_ALARM: config_entry.data.get(D_UPDATE_INTERVAL_ALARM, 30),
            D_UPDATE_INTERVAL_DATA: config_entry.data.get(D_UPDATE_INTERVAL_DATA, 60),
            D_BASE_API_URL: config_entry.data.get(D_BASE_API_URL, BASE_API_URL),
            D_RELATIONS_KEY: relations,
        }

        # set versions to ensure future migrations are correctly applied
        current_version = 2
        current_minor_version = 0
        clear_registry_entries = True
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
        if clear_registry_entries:
            _LOGGER.info(
                "Migration: clearing old registry entries for config entry %s",
                config_entry.entry_id,
            )
            dr.async_get(hass).async_clear_config_entry(config_entry.entry_id)
            er.async_get(hass).async_clear_config_entry(config_entry.entry_id)

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
