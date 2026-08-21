"""Tests for DiveraControl utils.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.diveracontrol.const import (
    D_CLUSTER_ID,
    D_COORDINATOR,
    D_RELATIONS_KEY,
    DOMAIN,
)
from custom_components.diveracontrol.utils import (
    get_cluster_coordinators_ucrs_from_config_hass,
    get_translation,
    get_ucr_data_from_device,
)


class TestGetUcrDataFromDevice:
    """Test the get_ucr_data_from_device function."""

    def test_get_ucr_data_from_device_success(self, hass: HomeAssistant) -> None:
        """Test getting ucr data from device successfully."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}
        mock_device.identifiers = [(DOMAIN, "test_ucr_id")]

        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_entry.data = {D_CLUSTER_ID: "test_cluster"}

        mock_coordinator = MagicMock()
        mock_coordinator.test_key = "test_value"

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device
            hass.data = {
                DOMAIN: {
                    "test_cluster": {
                        D_COORDINATOR: {"test_ucr_id": mock_coordinator}
                    }
                }
            }

            result = get_ucr_data_from_device(hass, "device1")
            assert result == mock_coordinator

    def test_get_ucr_data_from_device_with_key(self, hass: HomeAssistant) -> None:
        """Test getting specific key from coordinator."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}
        mock_device.identifiers = [(DOMAIN, "test_ucr_id")]

        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_entry.data = {D_CLUSTER_ID: "test_cluster"}

        mock_coordinator = MagicMock()
        mock_coordinator.test_key = "test_value"

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device
            hass.data = {
                DOMAIN: {
                    "test_cluster": {
                        D_COORDINATOR: {"test_ucr_id": mock_coordinator}
                    }
                }
            }

            result = get_ucr_data_from_device(hass, "device1", "test_key")
            assert result == "test_value"

    def test_get_ucr_data_from_device_not_found(self, hass: HomeAssistant) -> None:
        """Test error when device not found."""
        with patch(
            "custom_components.diveracontrol.utils.dr.async_get"
        ) as mock_device_registry:
            mock_device_registry.return_value.async_get.return_value = None

            with pytest.raises(HomeAssistantError, match="Device not found"):
                get_ucr_data_from_device(hass, "nonexistent")

    def test_get_ucr_data_from_device_no_ucr_id(self, hass: HomeAssistant) -> None:
        """Test error when device has no ucr_id identifier."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}
        mock_device.identifiers = []

        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_entry.data = {D_CLUSTER_ID: "test_cluster"}

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device

            with pytest.raises(HomeAssistantError, match="UCR ID not found"):
                get_ucr_data_from_device(hass, "device1")


class TestGetClusterCoordinatorsUcrsFromConfigHass:
    """Test the get_cluster_coordinators_ucrs_from_config_hass function."""

    def test_get_cluster_coordinators_ucrs_from_config_hass(
        self, hass: HomeAssistant
    ) -> None:
        """Test extracting cluster data from config entry."""
        config_data = {
            D_CLUSTER_ID: "test_cluster",
            D_RELATIONS_KEY: {"ucr1": {}, "ucr2": {}},
        }
        hass.data = {
            DOMAIN: {
                "test_cluster": {
                    D_COORDINATOR: {"ucr1": "coordinator1", "ucr2": "coordinator2"}
                }
            }
        }

        cluster_id, coordinators, ucrs = get_cluster_coordinators_ucrs_from_config_hass(
            config_data, hass
        )

        assert cluster_id == "test_cluster"
        assert coordinators == {"ucr1": "coordinator1", "ucr2": "coordinator2"}
        assert ucrs == {"ucr1": {}, "ucr2": {}}


@pytest.mark.asyncio
class TestGetTranslation:
    """Test the get_translation function."""

    async def test_get_translation_simple(self, hass: HomeAssistant) -> None:
        """Test get_translation with simple translation."""
        translations = {
            "component.diveracontrol.test_category.test_key": "Test message"
        }

        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value=translations,
        ):
            result = await get_translation(hass, "test_category", "test_key")

            assert result == "Test message"

    async def test_get_translation_with_placeholders(self, hass: HomeAssistant) -> None:
        """Test get_translation with placeholders."""
        translations = {
            "component.diveracontrol.test_category.test_key": "Error for {item}"
        }

        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value=translations,
        ):
            result = await get_translation(
                hass,
                "test_category",
                "test_key",
                {"item": "device1"},
            )

            assert result == "Error for device1"

    async def test_get_translation_missing_key(self, hass: HomeAssistant) -> None:
        """Test get_translation with missing translation key."""
        translations = {}

        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value=translations,
        ):
            result = await get_translation(hass, "test_category", "missing_key")

            assert (
                result == "component.diveracontrol.test_category.missing_key"
            )
