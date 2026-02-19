"""Tests for DiveraControl diagnostics."""

from pathlib import Path
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol.const import D_API_KEY, D_CLUSTER_NAME, DOMAIN
from custom_components.diveracontrol.diagnostics import (
    async_get_config_entry_diagnostics,
    get_diveracontrol_logs,
)


def test_get_diveracontrol_logs_file_missing(hass: HomeAssistant) -> None:
    """Test logfile helper returns fallback message when logfile is missing."""
    hass.config.path = MagicMock(return_value="/tmp/does-not-exist-diveracontrol.log")

    logs = get_diveracontrol_logs(hass)

    assert logs == ["Logfile not found."]


def test_get_diveracontrol_logs_filters_lines(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """Test logfile helper only returns lines containing diveracontrol."""
    log_file = tmp_path / "home-assistant.log"
    log_file.write_text(
        "INFO startup\n"
        "ERROR diveracontrol failed\n"
        "INFO DiveraControl mixed case\n"
        "DEBUG diveracontrol update\n",
        encoding="utf-8",
    )

    hass.config.path = MagicMock(return_value=str(log_file))

    logs = get_diveracontrol_logs(hass)

    assert logs == [
        "ERROR diveracontrol failed\n",
        "DEBUG diveracontrol update\n",
    ]


async def test_async_get_config_entry_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics response redacts API/access keys in config and cluster data."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Cluster",
        data={D_API_KEY: "secret_api_key", "plain": "ok"},
    )
    config_entry.runtime_data = MagicMock(
        data={"accesskey": "secret_access", "value": 123}
    )

    hass.config.path = MagicMock(return_value="/tmp/no-diagnostics-log.log")

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics[D_CLUSTER_NAME] == "Test Cluster"
    assert diagnostics["config_entry data"][D_API_KEY] == "**REDACTED**"
    assert diagnostics["config_entry data"]["plain"] == "ok"
    assert diagnostics["cluster data"]["accesskey"] == "**REDACTED**"
    assert diagnostics["cluster data"]["value"] == 123
    assert diagnostics["logs"] == ["Logfile not found."]
