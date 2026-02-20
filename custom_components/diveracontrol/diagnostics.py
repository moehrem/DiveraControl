"""Diagnostics for integration DiveraControl."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_API_KEY, D_CLUSTER_NAME
from .log_handler import async_get_diveracontrol_logs

TO_REDACT = [D_API_KEY, "accesskey"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, object]:
    """Return diagnostics for the integration including config_entry and coordinator data.

    Attention: Only api_keys and accesskeys are redacted. Any further personal data, i.e. names,
    telephone numbers, qualifications are shown and must be handled carefully!

    Args:
        hass (HomeAssistant): Home Assistant instance.
        config_entry (ConfigEntry): ConfigEntry instance for the integration

    Returns:
        dict: dictionary containing diagnostics data:
            - cluster/unit name
            - configuration entry data
            - cluster/coordinator data
            - logs related to DiveraControl

    """

    coordinator_data = config_entry.runtime_data.data

    logs = await async_get_diveracontrol_logs(hass)

    return async_redact_data(
        {
            D_CLUSTER_NAME: config_entry.title,
            "config_entry data": config_entry.data,
            "cluster data": coordinator_data,
            "logs": logs,
        },
        TO_REDACT,
    )
