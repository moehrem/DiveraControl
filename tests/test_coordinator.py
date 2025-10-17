"""Tests for DiveraControl coordinator."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.diveracontrol.coordinator import DiveraCoordinator
from custom_components.diveracontrol.divera_api import DiveraAPI


async def test_coordinator_update_failed(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test coordinator handles update failures correctly.

    Scenario:
    - The coordinator attempts to fetch data from the API.
    - The API call raises an exception.
    - The coordinator raises UpdateFailed exception.

    This test covers lines 91-92 (the except Exception block).

    """
    # Create a mock API that raises an exception
    mock_api = AsyncMock(spec=DiveraAPI)
    mock_api.get_ucr_data = AsyncMock(side_effect=Exception("API connection failed"))

    # Create coordinator with the failing API
    coordinator = DiveraCoordinator(
        hass=hass,
        api=mock_api,
        config_entry=mock_config_entry,
    )

    # Mock update_data to raise an exception
    with patch(
        "custom_components.diveracontrol.coordinator.update_data",
        side_effect=Exception("Test error"),
    ):
        # Attempt to update should raise UpdateFailed
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        # Verify the error message
        assert "Error fetching data: Test error" in str(exc_info.value)


async def test_coordinator_initialization(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test coordinator initialization.

    Scenario:
    - A coordinator is created with a config entry.
    - The coordinator correctly initializes with config data.
    - Update intervals are properly set.

    """
    from custom_components.diveracontrol.const import (
        D_CLUSTER_NAME,
        D_UCR_ID,
        D_UPDATE_INTERVAL_ALARM,
        D_UPDATE_INTERVAL_DATA,
    )

    # Create a mock API
    mock_api = AsyncMock(spec=DiveraAPI)

    # Create coordinator
    coordinator = DiveraCoordinator(
        hass=hass,
        api=mock_api,
        config_entry=mock_config_entry,
    )

    # Verify coordinator properties
    assert coordinator.cluster_name == mock_config_entry.data[D_CLUSTER_NAME]
    assert coordinator.ucr_id == mock_config_entry.data[D_UCR_ID]
    assert coordinator.api == mock_api

    # Verify update intervals
    assert D_UPDATE_INTERVAL_ALARM in coordinator.interval_data
    assert D_UPDATE_INTERVAL_DATA in coordinator.interval_data

    # Verify coordinator name
    expected_name = f"DiveraCoordinator_{mock_config_entry.data[D_UCR_ID]}"
    assert coordinator.name == expected_name


async def test_coordinator_dynamic_update_interval(
    hass: HomeAssistant,
    mock_config_entry,
    api_get_pull_all_response: dict,
) -> None:
    """Test that coordinator dynamically adjusts update interval.

    Scenario:
    - The coordinator fetches data from the API.
    - The update interval is adjusted based on alarm status.
    - The coordinator's update_interval property reflects the change.

    """
    # Mock update_data and set_update_interval
    with (
        patch(
            "custom_components.diveracontrol.coordinator.update_data",
            return_value=api_get_pull_all_response.get("data", {}),
        ),
        patch(
            "custom_components.diveracontrol.coordinator.set_update_interval",
            return_value=None,
        ) as mock_set_interval,
    ):
        # Create a mock API
        mock_api = AsyncMock(spec=DiveraAPI)

        # Create coordinator
        coordinator = DiveraCoordinator(
            hass=hass,
            api=mock_api,
            config_entry=mock_config_entry,
        )

        # Trigger update
        await coordinator._async_update_data()

        # Verify set_update_interval was called
        mock_set_interval.assert_called_once()
