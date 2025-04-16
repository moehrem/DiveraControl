"""Diagnostics for integration DiveraControl."""

from pathlib import Path

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_API_KEY, D_CLUSTER_NAME, D_COORDINATOR, D_UCR_ID, DOMAIN, LOG_FILE

TO_REDACT = [D_API_KEY, "accesskey"]


def get_diveracontrol_logs(hass: HomeAssistant):
    """Read logfile for entries related to DiveraControl, return the entries."""
    log_file = Path(hass.config.path(LOG_FILE))
    if not log_file.exists():
        return "Logfile not found."

    with log_file.open("r", encoding="utf-8") as file:
        return [line for line in file if "diveracontrol" in line]


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
