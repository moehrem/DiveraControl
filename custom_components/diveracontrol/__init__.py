"""Initializing DiveraControl integration."""

import asyncio
import logging

# IMPORTANT: import log_handler BEFORE any other module that uses logging to ensure the handler is registered in time
from .log_handler import (
    async_remove_diveracontrol_log_handler,
    async_setup_diveracontrol_log_handler,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from .const import (
    BASE_API_URL,
    D_ACCESSKEY,
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
    D_USERNAME,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)
from .coordinator import DiveraCoordinator
from .divera_api import DiveraAPIClient
from .service import async_register_services
from .utils import get_cluster_coordinators_ucrs_from_config_hass

PLATFORMS: list[Platform] = [
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

    cluster_id, _, ucrs = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )

    cluster_name: str = config_entry.data.get(D_CLUSTER_NAME) or ""

    _LOGGER.debug("Setting up cluster: %s (%s)", cluster_name, cluster_id)
    async_setup_diveracontrol_log_handler(hass)

    # Create coordinator instances per user relation.
    # every ucr has its own access key
    # update intervals and base-urls are shared on cluster level, so they are stored in the main config entry and not in the relation data
    coordinators: dict[str, DiveraCoordinator] = {}

    # First initialize all coordinators (setup API clients)
    setup_tasks = []
    ucr_info = []

    for (
        ucr_id,
        user_relation_data,
    ) in ucrs.items():
        # validate user_relation_data type
        if not isinstance(user_relation_data, dict):
            _LOGGER.error(
                "Invalid user relation data for ID %s: expected dict, got %s",
                ucr_id,
                type(user_relation_data).__name__,
            )
            continue

        # extract user_name with default
        user_name = user_relation_data.get(D_USERNAME, "unknown user")
        if user_name == "unknown user":
            _LOGGER.warning(
                "No username provided for ucr_id %s in cluster %s, using default",
                ucr_id,
                cluster_name,
            )

        # create coordinator and store info for setup task
        try:
            coordinator = DiveraCoordinator(hass, config_entry, ucr_id)
            ucr_info.append((ucr_id, user_name, coordinator))
            coordinators[ucr_id] = coordinator  # Add coordinator immediately
            setup_tasks.append(coordinator._async_setup())
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error creating coordinator for cluster %s, user %s (ID: %s): %s",
                cluster_name,
                user_name,
                ucr_id,
                err,
            )

    # Wait for all setup tasks to complete
    if setup_tasks:
        setup_results = await asyncio.gather(*setup_tasks, return_exceptions=True)

        # Process setup results and remove failed coordinators
        for (ucr_id, user_name, coordinator), result in zip(ucr_info, setup_results):
            if isinstance(result, Exception):
                # Handle setup errors
                if isinstance(result, ConfigEntryNotReady):
                    _LOGGER.error(
                        "Config entry not ready for cluster %s, user %s: %s",
                        cluster_name,
                        user_name,
                        result,
                    )
                elif isinstance(result, ConfigEntryAuthFailed):
                    _LOGGER.error(
                        "Authentication failed for cluster %s, user %s: %s",
                        cluster_name,
                        user_name,
                        result,
                    )
                elif isinstance(result, (TimeoutError, ConnectionError)):
                    _LOGGER.error(
                        "Connection failed for cluster %s, user %s: %s",
                        cluster_name,
                        user_name,
                        result,
                    )
                else:
                    _LOGGER.exception(
                        "Unexpected error during setup for cluster %s, user %s (ID: %s): %s",
                        cluster_name,
                        user_name,
                        ucr_id,
                        result,
                    )
                # Remove failed coordinator
                coordinators.pop(ucr_id, None)
            else:
                _LOGGER.debug(
                    "Successfully initialized coordinator for user %s (ID: %s)",
                    user_name,
                    ucr_id,
                )

    # Prepare refresh tasks only for successfully initialized coordinators
    refresh_tasks = []
    task_to_coordinator = {}  # Map tasks to their coordinators
    coordinator_to_ucr = {coord: (uid, uname) for uid, uname, coord in ucr_info}

    for coordinator in coordinators.values():
        # Start refresh immediately as a background task
        task = asyncio.create_task(coordinator.async_config_entry_first_refresh())
        task_to_coordinator[task] = coordinator  # Map task to coordinator
        refresh_tasks.append(task)

    # Wait for all refresh tasks to complete with a timeout
    if refresh_tasks:
        try:
            done, pending = await asyncio.wait(
                refresh_tasks,
                timeout=10.0,
                return_when=asyncio.ALL_COMPLETED,
            )

            # Cancel pending tasks to avoid hanging
            for task in pending:
                task.cancel()

            # Process results from completed tasks
            for task in done:
                try:
                    result = await task
                    coordinator = task_to_coordinator.get(
                        task
                    )  # Get coordinator from task
                    if coordinator is None:
                        _LOGGER.warning("Could not find coordinator for task %s", task)
                        continue

                    # Find the user_name and ucr_id for this coordinator
                    ucr_id, user_name = coordinator_to_ucr.get(
                        coordinator, (None, "unknown")
                    )

                    if ucr_id is None:
                        _LOGGER.warning(
                            "Could not find UCR ID for coordinator %s", coordinator
                        )
                        continue

                    if isinstance(result, Exception):
                        # Handle errors from async_config_entry_first_refresh
                        if isinstance(result, ConfigEntryNotReady):
                            _LOGGER.error(
                                "Config entry not ready for cluster %s, user %s: %s",
                                cluster_name,
                                user_name,
                                result,
                            )
                            coordinators.pop(ucr_id, None)  # Remove failed coordinator
                        elif isinstance(result, ConfigEntryAuthFailed):
                            _LOGGER.error(
                                "Authentication failed for cluster %s, user %s: %s",
                                cluster_name,
                                user_name,
                                result,
                            )
                            coordinators.pop(ucr_id, None)  # Remove failed coordinator
                        elif isinstance(result, (TimeoutError, ConnectionError)):
                            _LOGGER.error(
                                "Connection failed for cluster %s, user %s: %s",
                                cluster_name,
                                user_name,
                                result,
                            )
                        else:
                            _LOGGER.exception(
                                "Unexpected error during refresh for cluster %s, user %s (ID: %s): %s",
                                cluster_name,
                                user_name,
                                ucr_id,
                                result,
                            )
                    else:
                        _LOGGER.debug(
                            "Successfully refreshed data for user %s (ID: %s)",
                            user_name,
                            ucr_id,
                        )
                except asyncio.CancelledError:
                    pass  # Task was cancelled, ignore
                except Exception as err:
                    _LOGGER.exception(
                        "Unexpected error while processing refresh task: %s", err
                    )
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout while waiting for refresh tasks to complete")
            # Cancel all tasks on timeout
            for task in refresh_tasks:
                task.cancel()

    # Execute all refresh tasks in parallel (only for successfully initialized coordinators)
    if refresh_tasks:
        results = await asyncio.gather(*refresh_tasks, return_exceptions=True)

        # Process refresh results
        for (ucr_id, user_name, coordinator), result in zip(ucr_info, results):
            if ucr_id not in coordinators:
                continue  # Skip if setup failed

            if isinstance(result, Exception):
                # Handle errors from async_config_entry_first_refresh
                if isinstance(result, ConfigEntryNotReady):
                    _LOGGER.error(
                        "Config entry not ready for cluster %s, user %s: %s",
                        cluster_name,
                        user_name,
                        result,
                    )
                    coordinators.pop(ucr_id, None)  # Remove failed coordinator
                elif isinstance(result, ConfigEntryAuthFailed):
                    _LOGGER.error(
                        "Authentication failed for cluster %s, user %s: %s",
                        cluster_name,
                        user_name,
                        result,
                    )
                    coordinators.pop(ucr_id, None)  # Remove failed coordinator
                elif isinstance(result, (TimeoutError, ConnectionError)):
                    _LOGGER.error(
                        "Connection failed for cluster %s, user %s: %s",
                        cluster_name,
                        user_name,
                        result,
                    )
                else:
                    _LOGGER.exception(
                        "Unexpected error during refresh for cluster %s, user %s (ID: %s): %s",
                        cluster_name,
                        user_name,
                        ucr_id,
                        result,
                    )
            else:
                _LOGGER.debug(
                    "Successfully refreshed data for user %s (ID: %s)",
                    user_name,
                    ucr_id,
                )

    if not coordinators:
        raise ConfigEntryNotReady("Failed to set up any user for this cluster")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][cluster_id] = {
        D_COORDINATOR: coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    _LOGGER.debug(
        "Setting up cluster %s (%s users) successfully",
        cluster_name,
        len(coordinators),
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

    user_cluster_relations = config_entry.data.get(D_RELATIONS_KEY, {})
    if not isinstance(user_cluster_relations, dict):
        return False

    if ucr_id not in user_cluster_relations:
        return False

    # Keep at least one relation in the entry; removing the last one would
    # leave an invalid cluster config entry.
    if len(user_cluster_relations) <= 1:
        _LOGGER.warning(
            "Cannot remove last user relation %s from cluster %s",
            ucr_id,
            config_entry.data.get(D_CLUSTER_ID, "unknown"),
        )
        return False

    updated_relations = dict(user_cluster_relations)
    updated_relations.pop(ucr_id, None)
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            **config_entry.data,
            D_RELATIONS_KEY: updated_relations,
        },
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await asyncio.sleep(
        0.1
    )  # allow HA to process the reload before returning, thus avoiding race conditions

    _LOGGER.info(
        "Removed user relation %s from cluster %s via device deletion",
        ucr_id,
        config_entry.data.get(D_CLUSTER_ID, "unknown"),
    )
    return True


def _remove_old_entity_entries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Remove all existing entity registry entries for a config entry during migration."""
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


def _migrate_to_v1_2_0(
    updated_data: dict,
    config_entry: ConfigEntry,
    hass: HomeAssistant,
) -> tuple[dict, int, int, bool]:
    """Migrate to v1.2.0: Add integration_version and create breaking changes issue."""
    _LOGGER.info("Migrating config entry to integration version 1.2.0")
    current_version = 1
    current_minor_version = 2
    migrated = False

    if D_INTEGRATION_VERSION not in updated_data:
        _LOGGER.info("Adding integration version to existing config entry")
        updated_data[D_INTEGRATION_VERSION] = (
            f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
        )
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
    _remove_old_entity_entries(hass, config_entry)

    return updated_data, current_version, current_minor_version, migrated


def _migrate_to_v1_3_0(
    updated_data: dict,
) -> tuple[dict, int, int, bool]:
    """Migrate to v1.3.0: Add base_api_url parameter."""
    _LOGGER.info("Migrating config entry to integration version 1.3.0")
    current_version = 1
    current_minor_version = 3
    migrated = False

    if D_BASE_API_URL not in updated_data:
        _LOGGER.info("Adding base_url to existing config entry")
        updated_data[D_BASE_API_URL] = BASE_API_URL
        updated_data[D_INTEGRATION_VERSION] = (
            f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
        )
        migrated = True

    return updated_data, current_version, current_minor_version, migrated


def _migrate_to_v1_4_0(
    updated_data: dict,
) -> tuple[dict, int, int, bool]:
    """Migrate to v1.4.0: Add use_webhooks parameter."""
    _LOGGER.info("Migrating config entry to integration version 1.4.0")
    current_version = 1
    current_minor_version = 4
    migrated = False

    if D_USE_WEBHOOKS not in updated_data:
        _LOGGER.info("Adding use_webhooks to existing config entry")
        updated_data[D_USE_WEBHOOKS] = False
        updated_data[D_INTEGRATION_VERSION] = (
            f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
        )
        migrated = True

    return updated_data, current_version, current_minor_version, migrated


async def _migrate_to_v2_0_0(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    updated_data: dict,
) -> tuple[dict, int, int, bool] | None:
    """Migrate to v2.0.0: Restructure config to support multiple users per cluster.

    Returns None if migration fails, otherwise returns (updated_data, current_version, current_minor_version, migrated).
    """
    _LOGGER.info("Migrating config entry to integration version 2.0.0")

    user_input = {
        D_ACCESSKEY: config_entry.data.get("api_key", ""),
    }
    base_api_url = config_entry.data.get(D_BASE_API_URL, BASE_API_URL)

    config_api = DiveraAPIClient(hass, base_api_url)
    validation_errors, clusters = await config_api.request_access(user_input)

    if validation_errors:
        _LOGGER.error(
            "API key validation failed during migration: %s", validation_errors
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
        return None

    ucr_id: str = config_entry.data.get(D_UCR_ID, "")
    migrated_cluster: dict | None = next(
        (c for c in clusters.values() if c.get(D_RELATIONS_KEY, {}).get(ucr_id)),
        None,
    )

    if migrated_cluster is None:
        _LOGGER.error(
            "No matching cluster found for UCR_ID %s during migration to v2.0.0", ucr_id
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
        return None

    raw_relations: dict = migrated_cluster.pop(D_RELATIONS_KEY, {})
    user_cluster_relations: dict[str, dict] = {}
    for raw_ucr_id, raw_relation_data in raw_relations.items():
        if not isinstance(raw_relation_data, dict):
            continue

        ucr_id = str(raw_ucr_id)
        relation_data = dict(raw_relation_data)
        relation_data.pop(D_BASE_API_URL, None)
        relation_data.pop(D_UPDATE_INTERVAL_DATA, None)
        relation_data.pop(D_UPDATE_INTERVAL_ALARM, None)
        relation_data.pop(D_UCR_ID, None)  # Remove redundant UCR_ID from relation data
        user_cluster_relations[ucr_id] = relation_data

    updated_data = {
        **migrated_cluster,
        D_UPDATE_INTERVAL_ALARM: config_entry.data.get(D_UPDATE_INTERVAL_ALARM, 30),
        D_UPDATE_INTERVAL_DATA: config_entry.data.get(D_UPDATE_INTERVAL_DATA, 60),
        D_BASE_API_URL: config_entry.data.get(D_BASE_API_URL, BASE_API_URL),
        D_RELATIONS_KEY: user_cluster_relations,
    }

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

    return updated_data, current_version, current_minor_version, migrated


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config_entry to the respective version.

    Note: config_entry.version and config_entry.minor_version are the CONFIG ENTRY
    SCHEMA version numbers. They must be explicitly set during migration to match
    the versions defined in ConfigFlow (VERSION and MINOR_VERSION).

    """

    updated_data: dict = {**config_entry.data}
    clear_registry_entries: bool = False
    migrated: bool = False

    current_version: int = config_entry.version
    current_minor_version: int = config_entry.minor_version
    current_patch_version: str = (
        config_entry.data.get(D_INTEGRATION_VERSION, "0.0.0").split(".")[2]
        or PATCH_VERSION
        or "0"
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

    # Apply migrations in order using helper functions
    # v1.2.0: Add integration_version parameter and create breaking changes issue
    if current_version == 1 and current_minor_version < 2:
        updated_data, current_version, current_minor_version, migrated = (
            _migrate_to_v1_2_0(updated_data, config_entry, hass)
        )

    # v1.3.0: Add base_url parameter
    if current_version == 1 and current_minor_version < 3:
        updated_data, current_version, current_minor_version, migrated = (
            _migrate_to_v1_3_0(updated_data)
        )

    # v1.4.0: Add use_webhooks parameter
    if current_version == 1 and current_minor_version < 4:
        updated_data, current_version, current_minor_version, migrated = (
            _migrate_to_v1_4_0(updated_data)
        )

    # v2.0.0: Breaking change - restructure config to support multiple users per cluster
    if current_version == 1 and current_minor_version < 5:
        migration_result = await _migrate_to_v2_0_0(hass, config_entry, updated_data)
        if migration_result is None:
            return False
        updated_data, current_version, current_minor_version, migrated = (
            migration_result
        )
        clear_registry_entries = True  # to ensure all old entities are removed, as the config structure changed significantly and old entities would not be cleaned up properly due to missing UCR_ID in their unique_ids

    # Finalize migration by updating config entry version if any migration step was performed
    if migrated or current_version != VERSION or current_minor_version != MINOR_VERSION:
        if clear_registry_entries:
            _LOGGER.info(
                "Migration: clearing old registry entries for config entry %s due to breaking changes",
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
