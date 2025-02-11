"""Handles permission requests."""

import logging
import re

import homeassistant.helpers.entity_registry as er

from .const import (
    DOMAIN,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    D_USER,
    D_ACCESS,
    D_HUB_ID,
    D_UCR,
    PERM_MANAGEMENT,
)

LOGGER = logging.getLogger(__name__)


def permission_request(data, perm_key):
    """Return permission to access data."""

    management = data.get(D_ACCESS, {}).get(PERM_MANAGEMENT)
    permission = data.get(D_ACCESS, {}).get(perm_key)

    if management:
        access = management
    elif permission:
        access = permission
    else:
        access = False

    if not access:
        hub_id = data.get(D_HUB_ID, "")
        unit_name = data.get(D_UCR, {}).get(hub_id, "").get("name", "Unknown")
        LOGGER.warning(
            "Permission denied to access %s for unit '%s'",
            perm_key.upper(),
            unit_name,
        )

    return access


def sanitize_entity_id(name):
    """Replace not allowed symbols within entity ids."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


class BaseDiveraEntity:
    """Gemeinsame Basisklasse für Sensoren und Tracker."""

    def __init__(self, coordinator, ucr_data, ucr_id: str) -> None:
        """Initialisiert die gemeinsame Basisklasse."""
        self.coordinator = coordinator
        self.cluster_id = coordinator.cluster_id
        self.ucr_id = ucr_id
        self.ucr_data = ucr_data

    @property
    def device_info(self):
        """Gibt Geräteinformationen zurück."""
        firstname = self.ucr_data.get(D_USER, {}).get("firstname", "")
        lastname = self.ucr_data.get(D_USER, {}).get("lastname", "")
        return {
            "identifiers": {(DOMAIN, f"{firstname} {lastname}")},
            "name": f"{firstname} {lastname} / {self.ucr_id}",
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


def get_device_info(ucr_data, ucr_id):
    """Gibt Geräteinformationen für den Tracker zurück."""
    firstname = ucr_data.get(D_USER, {}).get("firstname", "")
    lastname = ucr_data.get(D_USER, {}).get("lastname", "")
    return {
        "identifiers": {(DOMAIN, f"{firstname} {lastname}")},
        "name": f"{firstname} {lastname} / {ucr_id}",
        "manufacturer": MANUFACTURER,
        "model": DOMAIN,
        "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        "entry_type": "service",
    }
