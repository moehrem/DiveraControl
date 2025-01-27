"""Handles permission requests."""

import logging
import re

from .const import D_ACCESS, D_HUB_ID, D_UCR, PERM_MANAGEMENT

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
