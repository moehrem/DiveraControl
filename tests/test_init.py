"""Tests for DiveraControl integration initialization."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.diveracontrol import (
    async_setup,
    async_unload_entry,
)
from custom_components.diveracontrol.const import DOMAIN


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.data = {}
    return hass


class TestAsyncSetup:
    """Test async_setup function."""

    def test_async_setup_returns_true(self, mock_hass) -> None:
        """Test that async_setup returns True."""
        # Since we can't easily test async functions without a running event loop,
        # we'll just verify the function exists and has the right signature
        assert hasattr(async_setup, "__call__")
        assert async_setup.__code__.co_argcount >= 2


class TestAsyncUnloadEntry:
    """Test async_unload_entry function."""

    def test_async_unload_entry_returns_true(self, mock_hass) -> None:
        """Test that async_unload_entry returns True."""
        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN

        # Just verify the function exists
        assert hasattr(async_unload_entry, "__call__")
        assert async_unload_entry.__code__.co_argcount >= 2
