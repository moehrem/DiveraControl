"""Tests for DiveraControl __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol import (
    async_setup,
    async_migrate_entry,
)
from custom_components.diveracontrol.const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_UCR_ID,
    DOMAIN,
    MINOR_VERSION,
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


async def test_async_migrate_entry_from_v0_8_fails(hass: HomeAssistant) -> None:
    """Test migration from version 0.8.x fails (not supported)."""
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
    
    assert result is False
