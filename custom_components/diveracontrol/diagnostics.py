"""Diagnostics for integration DiveraControl."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry

from .const import D_API_KEY, DOMAIN, D_COORDINATOR, D_CLUSTER_ID, D_CLUSTER_NAME

_LOGGER = logging.getLogger(__name__)

TO_REDACT = [D_API_KEY, "accesskey"]


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    """Return diagnostics for the integration including config_entry and coordinator data."""
    cluster_id = entry.data[D_CLUSTER_ID]
    cluster_data = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    return async_redact_data(
        {
            D_CLUSTER_NAME: entry.title,
            "config_entry data": entry.data,
            "last update data": cluster_data._last_data_update,
            "last update alarm": cluster_data._last_alarm_update,
            "cluster data": cluster_data.cluster_data,
        },
        TO_REDACT,
    )
