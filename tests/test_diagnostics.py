"""Tests for DiveraControl diagnostics."""

import logging
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol.const import (
    D_ACCESSKEY,
    D_CLUSTER_NAME,
    DOMAIN,
)
from custom_components.diveracontrol.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.diveracontrol.log_handler import (
    async_get_diveracontrol_logs,
    async_setup_diveracontrol_log_handler,
)


async def test_get_diveracontrol_logs_without_handler(hass: HomeAssistant) -> None:
    """Test in-memory logs return fallback message when handler is missing."""
    logs = await async_get_diveracontrol_logs(hass)

    assert logs == ["No in-memory logs available"]


async def test_get_diveracontrol_logs_uses_in_memory_handler(
    hass: HomeAssistant,
) -> None:
    """Test in-memory logs include diveracontrol logger entries."""
    async_setup_diveracontrol_log_handler(hass)

    divera_logger = logging.getLogger("custom_components.diveracontrol")
    other_logger = logging.getLogger("custom_components.other")
    divera_logger.warning("Divera warning")
    other_logger.warning("Other warning")

    logs = await async_get_diveracontrol_logs(hass)

    assert any("Divera warning" in line for line in logs)
    assert all("Other warning" not in line for line in logs)


async def test_async_get_config_entry_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics response redacts API/access keys in config and cluster data."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Cluster",
        data={D_ACCESSKEY: "secret_api_key", "plain": "ok"},
    )
    config_entry.runtime_data = MagicMock(
        data={"accesskey": "secret_access", "value": 123}
    )
    async_setup_diveracontrol_log_handler(hass)
    logging.getLogger("custom_components.diveracontrol").warning("Diagnostics test log")

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics[D_CLUSTER_NAME] == "Test Cluster"
    assert diagnostics["config_entry data"][D_ACCESSKEY] == "**REDACTED**"
    assert diagnostics["config_entry data"]["plain"] == "ok"
    assert diagnostics["cluster data"]["accesskey"] == "**REDACTED**"
    assert diagnostics["cluster data"]["value"] == 123
    assert any("Diagnostics test log" in line for line in diagnostics["logs"])
