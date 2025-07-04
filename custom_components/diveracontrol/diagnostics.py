"""Diagnostics for integration DiveraControl."""

from pathlib import Path

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_API_KEY, D_CLUSTER_NAME, D_COORDINATOR, D_UCR_ID, DOMAIN, LOG_FILE

TO_REDACT = [D_API_KEY, "accesskey"]


def get_diveracontrol_logs(hass: HomeAssistant) -> list:
    """Read logfile for entries related to DiveraControl, return the entries.

    Args:
        hass (HomeAssistant): Home Assistant instance.

    Returns:
        list: List of log entries containing string "diveracontrol",
              or a list with one string if the file is not found.

    """
    log_file = Path(hass.config.path(LOG_FILE))
    if not log_file.exists():
        return ["Logfile not found."]

    with log_file.open("r", encoding="utf-8") as file:
        return [line for line in file if "diveracontrol" in line]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict:
    """Return diagnostics for the integration including config_entry and coordinator data.

    Attention: Only api_keys and accesskeys are redacted in the logs. Any further personal data, i.e. names,
    telephone numbers, qualifications are shown and must be handled carefully!

    Args:
        hass (HomeAssistant): Home Assistant instance.
        entry (ConfigEntry): ConfigEntry instance for the intrgration

    Returns:
        dict: dictionary containing diagnostics data:
            - cluster/unit name
            - configuration entry data
            - cluster/coordinator data
            - logs related to DiveraControl

    """

    ucr_id = entry.data[D_UCR_ID]
    cluster_data = hass.data[DOMAIN][ucr_id][D_COORDINATOR].cluster_data
    admin_data = hass.data[DOMAIN][ucr_id][D_COORDINATOR].admin_data

    logs = await hass.async_add_executor_job(get_diveracontrol_logs, hass)

    return async_redact_data(
        {
            D_CLUSTER_NAME: entry.title,
            "config_entry data": entry.data,
            "admin_data": admin_data,
            "cluster data": cluster_data,
            "logs": logs,
        },
        TO_REDACT,
    )
