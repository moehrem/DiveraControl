"""Tests for DiveraControl __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol import (
    async_migrate_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.diveracontrol.const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_INTEGRATION_VERSION,
    D_UCR_ID,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test async_setup registers services."""
    result = await async_setup(hass, {})

    assert result is True
    assert hass.services.has_service(DOMAIN, "post_vehicle_status")
    assert hass.services.has_service(DOMAIN, "post_alarm")


async def test_async_migrate_entry_from_v0_9(hass: HomeAssistant) -> None:
    """Test migration from version 0.9.x to 1.0.0."""
    old_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Cluster",
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
        version=0,
        minor_version=9,
    )
    old_entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, old_entry)

    assert result is True
    assert old_entry.version == VERSION
    assert old_entry.minor_version == MINOR_VERSION


async def test_async_migrate_entry_from_v0_8_succeeds(hass: HomeAssistant) -> None:
    """Test migration from version 0.8.x succeeds (now supported)."""
    old_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Cluster",
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
        version=0,
        minor_version=8,
    )
    old_entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, old_entry)

    assert result is True
    assert D_INTEGRATION_VERSION in old_entry.data


@pytest.mark.parametrize(
    ("exception", "expected_exception"),
    [
        (TimeoutError("Connection timeout"), ConfigEntryNotReady),
        (ConnectionError("Connection failed"), ConfigEntryNotReady),
        (ConfigEntryAuthFailed("Auth failed"), ConfigEntryAuthFailed),
        (Exception("Unexpected error"), ConfigEntryNotReady),
    ],
)
async def test_async_setup_entry_failures(
    hass: HomeAssistant,
    exception: Exception,
    expected_exception: type[Exception],
) -> None:
    """Test async_setup_entry handles various exceptions correctly."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
    )

    with (
        patch("custom_components.diveracontrol.DiveraAPI") as mock_api_class,
        patch(
            "custom_components.diveracontrol.DiveraCoordinator"
        ) as mock_coordinator_class,
    ):
        mock_api = mock_api_class.return_value
        mock_coordinator = mock_coordinator_class.return_value

        # Setup the exception to be raised during coordinator refresh
        mock_coordinator.async_config_entry_first_refresh.side_effect = exception

        # Test that the expected exception is raised
        with pytest.raises(expected_exception):
            await async_setup_entry(hass, config_entry)


async def test_async_setup_entry_success(hass: HomeAssistant) -> None:
    """Test async_setup_entry succeeds with valid configuration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
    )

    with (
        patch("custom_components.diveracontrol.DiveraAPI") as mock_api_class,
        patch(
            "custom_components.diveracontrol.DiveraCoordinator"
        ) as mock_coordinator_class,
        patch("custom_components.diveracontrol.async_register_services"),
        patch.object(hass.config_entries, "async_forward_entry_setups") as mock_forward,
        patch.object(config_entry, "async_on_unload") as mock_async_on_unload,
    ):
        mock_api = mock_api_class.return_value
        mock_coordinator = mock_coordinator_class.return_value

        # Setup successful coordinator refresh
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
        mock_forward.return_value = None

        result = await async_setup_entry(hass, config_entry)

        assert result is True

        # Verify API and coordinator were created with correct parameters
        mock_api_class.assert_called_once_with(
            hass,
            "123456",
            "test_key",
        )
        mock_coordinator_class.assert_called_once_with(
            hass,
            mock_api,
            config_entry,
        )

        # Verify coordinator was stored in runtime_data and hass.data
        assert config_entry.runtime_data == mock_coordinator
        assert hass.data[DOMAIN]["123456"][D_COORDINATOR] == mock_coordinator

        # Verify platforms were forwarded
        mock_forward.assert_called_once_with(
            config_entry, ["calendar", "device_tracker", "sensor"]
        )

        # Verify cleanup was registered
        mock_async_on_unload.assert_called_once_with(mock_api.close)


async def test_async_unload_entry_success(hass: HomeAssistant) -> None:
    """Test async_unload_entry succeeds."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
    )

    # Setup hass.data structure
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["123456"] = {D_COORDINATOR: MagicMock()}

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=True
    ) as mock_unload:
        result = await async_unload_entry(hass, config_entry)

        assert result is True
        mock_unload.assert_called_once_with(
            config_entry, ["calendar", "device_tracker", "sensor"]
        )

        # Verify data was cleaned up
        assert DOMAIN not in hass.data


async def test_async_unload_entry_failure(hass: HomeAssistant) -> None:
    """Test async_unload_entry fails when platform unload fails."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
    )

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        result = await async_unload_entry(hass, config_entry)

        assert result is False


async def test_async_migrate_entry_v1_2_0(hass: HomeAssistant) -> None:
    """Test migration to version 1.2.0 adds integration version."""
    old_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Cluster",
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Test Cluster",
            D_API_KEY: "test_key",
        },
        version=1,
        minor_version=1,  # Before 1.2.0
    )
    old_entry.add_to_hass(hass)

    with (
        patch("custom_components.diveracontrol.VERSION", 1),
        patch("custom_components.diveracontrol.MINOR_VERSION", 2),
        patch("custom_components.diveracontrol.PATCH_VERSION", 0),
    ):
        result = await async_migrate_entry(hass, old_entry)

        assert result is True
        assert old_entry.version == 1
        assert old_entry.minor_version == 2
        assert D_INTEGRATION_VERSION in old_entry.data
        assert old_entry.data[D_INTEGRATION_VERSION] == "1.2.0"
