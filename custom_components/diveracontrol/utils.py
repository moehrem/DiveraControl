"""Handles permission requests."""

import logging
import re
import time
import asyncio
from functools import wraps

import homeassistant.helpers.entity_registry as er

from .const import (
    DOMAIN,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    D_CLUSTER_NAME,
    D_USER,
    D_ACCESS,
    D_HUB_ID,
    D_UCR,
    PERM_MANAGEMENT,
)

LOGGER = logging.getLogger(__name__)


def permission_request(coordinator_data, perm_key):
    """Return permission to access data."""

    cluster_name = coordinator_data.cluster_name
    management = coordinator_data.cluster_data.get("access", {}).get(PERM_MANAGEMENT)
    permission = coordinator_data.cluster_data.get("access", {}).get(perm_key)

    if management:
        sucess = management
    elif permission:
        sucess = permission
    else:
        sucess = False

    if not sucess:
        # raise DiveraPermissionDenied(
        #     f"Permission denied for {perm_key} in cluster {cluster_name}"
        # )
        LOGGER.warning("Permission denied for %s in cluster %s", perm_key, cluster_name)

    return sucess


class BaseDiveraEntity:
    """Gemeinsame Basisklasse für Sensoren und Tracker."""

    def __init__(self, coordinator, cluster_data, cluster_id: str) -> None:
        """Initialisiert die gemeinsame Basisklasse."""
        self.coordinator = coordinator
        # self.cluster_id = coordinator.cluster_id
        self.cluster_id = cluster_id
        self.cluster_data = cluster_data

    @property
    def device_info(self):
        """Gibt Geräteinformationen zurück."""
        unit_name = self.cluster_name
        # firstname = self.cluster_data.get(D_USER, {}).get("firstname", "")
        # lastname = self.cluster_data.get(D_USER, {}).get("lastname", "")
        return {
            "identifiers": {(DOMAIN, unit_name)},
            "name": unit_name,
            "manufacturer": MANUFACTURER,
            "model": DOMAIN,
            "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
            "entry_type": "service",
        }

    @property
    def should_poll(self) -> bool:
        """Gibt an, dass die Entität nicht gepollt werden muss."""
        return False

    async def async_added_to_hass(self) -> None:
        """Registriert die Entität im Koordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def remove_from_hass(self) -> None:
        """Entfernt die Entität vollständig aus Home Assistant."""
        LOGGER.debug("Starting removal process for entity: %s", self.entity_id)

        # Entferne aus dem Entity-Registry
        try:
            registry = er.async_get(self.hass)
            if registry.async_is_registered(self.entity_id):
                registry.async_remove(self.entity_id)
                LOGGER.debug("Removed entity from registry: %s", self.entity_id)
            else:
                LOGGER.debug("Entity not found in registry: %s", self.entity_id)
        except Exception as e:
            LOGGER.error(
                "Failed to remove entity from registry: %s, Error: %s",
                self.entity_id,
                e,
            )

        # Entferne aus der State-Machine
        try:
            self.hass.states.async_remove(self.entity_id)
            LOGGER.debug("Removed entity from state machine: %s", self.entity_id)
        except Exception as e:
            LOGGER.error(
                "Failed to remove entity from state machine: %s, Error: %s",
                self.entity_id,
                e,
            )

        # Entferne aus internen Datenstrukturen
        try:
            entity_type = (
                "sensors"
                if self.__class__.__name__ == "BaseDiveraSensor"
                else "trackers"
            )

            if DOMAIN in self.hass.data and self.cluster_id in self.hass.data[DOMAIN]:
                entities = self.hass.data[DOMAIN][self.cluster_id].get(entity_type, {})
                if self.entity_id in entities:
                    del entities[self.entity_id]
                    LOGGER.debug(
                        "Removed entity from internal storage: %s", self.entity_id
                    )
        except Exception as e:
            LOGGER.error(
                "Failed to remove entity from internal storage: %s, Error: %s",
                self.entity_id,
                e,
            )

        LOGGER.info("Entity successfully removed: %s", self.entity_id)


def get_device_info(cluster_name):
    """Gibt Geräteinformationen für den Tracker zurück."""
    unit_name = cluster_name
    # firstname = ucr_data.get(D_USER, {}).get("firstname", "")
    # lastname = ucr_data.get(D_USER, {}).get("lastname", "")
    return {
        "identifiers": {(DOMAIN, unit_name)},
        "name": unit_name,
        "manufacturer": MANUFACTURER,
        "model": DOMAIN,
        "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        "entry_type": "service",
    }


def log_execution_time(func):
    """Decorator to log execution time of functions (sync & async)."""

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            LOGGER.debug(
                "Execution time of %s: %.2f seconds", func.__name__, elapsed_time
            )
            return result

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            LOGGER.debug(
                "Execution time of %s: %.2f seconds", func.__name__, elapsed_time
            )
            return result

        return sync_wrapper


class DiveraAPIError(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        LOGGER.error("Authentifizierung bei Divera fehlgeschlagen: %s", str(error))


class DiveraPermissionDenied(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        LOGGER.warning("Zugriff auf Divera-API verweigert: %s", str(error))
