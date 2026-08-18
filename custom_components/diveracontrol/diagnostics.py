"""Diagnostics for integration DiveraControl."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_ACCESSKEY
from .log_handler import async_get_diveracontrol_logs
from .utils import get_cluster_coordinators_ucrs_from_config_hass

TO_REDACT = [D_ACCESSKEY, "accesskey"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, object]:
    """Return cluster and user data integration including config_entry and coordinator data.

    Attention: Only accesskeys are redacted. Any further personal data, i.e. names,
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

    _, coordinators, _ = get_cluster_coordinators_ucrs_from_config_hass(
        config_entry.data, hass
    )
    coordinator_data = {
        ucr_id: coordinator.data for ucr_id, coordinator in coordinators.items()
    }

    logs = await async_get_diveracontrol_logs(hass)

    return async_redact_data(
        {
            "config_entry": config_entry.data,
            "coordinators": coordinator_data,
            "logs": logs,
        },
        TO_REDACT,
    )
