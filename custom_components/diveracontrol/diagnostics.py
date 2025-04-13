"""Diagnostics for integration DiveraControl."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_API_KEY, D_UCR_ID, D_CLUSTER_NAME, D_COORDINATOR, DOMAIN

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
    ucr_id = entry.data[D_UCR_ID]
    cluster_data = hass.data[DOMAIN][ucr_id][D_COORDINATOR]

    logs = await hass.async_add_executor_job(get_diveracontrol_logs, hass)

    return async_redact_data(
        {
            D_CLUSTER_NAME: entry.title,
            "config_entry data": entry.data,
            "cluster data": cluster_data.cluster_data,
            "logs": logs,
        },
        TO_REDACT,
    )
