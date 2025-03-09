"""Diagnostics for integration DiveraControl."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry

from .const import D_API_KEY, DOMAIN, D_COORDINATOR, D_CLUSTER_ID, D_CLUSTER_NAME

TO_REDACT = [D_API_KEY, "accesskey"]

from pathlib import Path


def get_diveracontrol_logs(hass):
    log_file = Path(hass.config.path("home-assistant.log"))
    if not log_file.exists():
        return "Logdatei nicht gefunden."

    with log_file.open("r", encoding="utf-8") as file:
        return [line for line in file if "custom_components.diveracontrol" in line]


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    """Return diagnostics for the integration including config_entry and coordinator data."""
    cluster_id = entry.data[D_CLUSTER_ID]
    cluster_data = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    logs = await hass.async_add_executor_job(get_diveracontrol_logs, hass)

    return async_redact_data(
        {
            D_CLUSTER_NAME: entry.title,
            "config_entry data": entry.data,
            "last update data": cluster_data._last_data_update,
            "last update alarm": cluster_data._last_alarm_update,
            "cluster data": cluster_data.cluster_data,
            "logs": logs,
        },
        TO_REDACT,
    )
