"""Tests for DiveraControl divera_data.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError
from homeassistant.exceptions import HomeAssistantError

from custom_components.diveracontrol.const import (
    D_ALARM,
    D_CLUSTER,
    D_DATA,
    D_DM,
    D_EVENTS,
    D_LOCALMONITOR,
    D_MESSAGE,
    D_MESSAGE_CHANNEL,
    D_MONITOR,
    D_NEWS,
    D_OPEN_ALARMS,
    D_STATUS,
    D_STATUSPLAN,
    D_TS,
    D_UCR,
    D_UCR_ACTIVE,
    D_UCR_DEFAULT,
    D_USER,
    D_VEHICLE,
)
from custom_components.diveracontrol.divera_data import (
    _convert_empty_lists_to_dicts,
    update_data,
)


class TestConvertEmptyListsToDicts:
    """Test the _convert_empty_lists_to_dicts function."""

    def test_convert_empty_lists_simple(self) -> None:
        """Test converting simple empty lists to dicts."""
        data = {"key1": [], "key2": "value", "key3": {}}
        result = _convert_empty_lists_to_dicts(data)

        assert result == {"key1": {}, "key2": "value", "key3": {}}

    def test_convert_empty_lists_nested(self) -> None:
        """Test converting empty lists in nested structures."""
        data = {
            "level1": {
                "level2": {
                    "empty_list": [],
                    "filled_list": [1, 2, 3],
                    "nested_empty": {"another_empty": []},
                },
                "simple_empty": [],
            },
            "root_empty": [],
        }
        result = _convert_empty_lists_to_dicts(data)

        expected = {
            "level1": {
                "level2": {
                    "empty_list": {},
                    "filled_list": [1, 2, 3],
                    "nested_empty": {"another_empty": {}},
                },
                "simple_empty": {},
            },
            "root_empty": {},
        }
        assert result == expected

    def test_convert_no_empty_lists(self) -> None:
        """Test that non-empty data is unchanged."""
        data = {
            "key1": "value",
            "key2": {"nested": "data"},
            "key3": [1, 2, 3],
            "key4": 42,
        }
        result = _convert_empty_lists_to_dicts(data)

        assert result == data

    def test_convert_mixed_data_types(self) -> None:
        """Test conversion with various data types."""
        data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "none_value": None,
            "empty_list": [],
            "filled_list": [1, 2, 3],
            "empty_dict": {},
            "nested": {"empty_nested": [], "filled_nested": {"key": "value"}},
        }
        result = _convert_empty_lists_to_dicts(data)

        expected = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "none_value": None,
            "empty_list": {},
            "filled_list": [1, 2, 3],
            "empty_dict": {},
            "nested": {"empty_nested": {}, "filled_nested": {"key": "value"}},
        }
        assert result == expected


class TestUpdateData:
    """Test the update_data function."""

    @pytest.fixture
    def mock_api(self) -> MagicMock:
        """Create a mock API instance."""
        api = MagicMock()
        api.get_ucr_data = AsyncMock()
        api.get_vehicle_property = AsyncMock()
        return api

    @pytest.fixture
    def initial_cluster_data(self) -> dict:
        """Create initial cluster data structure."""
        return {}

    async def test_update_data_initializes_empty_cluster_data(
        self, mock_api: MagicMock
    ) -> None:
        """Test that update_data initializes empty cluster_data correctly."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_UCR: {"ucr_data": "test"},
                D_USER: {"user_data": "test"},
                D_STATUS: {"status_data": "test"},
            },
        }

        result = await update_data(mock_api, cluster_data)

        # Check that all required keys are initialized
        required_keys = [
            D_UCR,
            D_UCR_DEFAULT,
            D_UCR_ACTIVE,
            D_TS,
            D_USER,
            D_STATUS,
            D_CLUSTER,
            D_MONITOR,
            D_ALARM,
            D_NEWS,
            D_EVENTS,
            D_DM,
            D_MESSAGE_CHANNEL,
            D_MESSAGE,
            D_LOCALMONITOR,
            D_STATUSPLAN,
        ]
        for key in required_keys:
            assert key in result
            assert isinstance(result[key], dict)

    async def test_update_data_successful_update(self, mock_api: MagicMock) -> None:
        """Test successful data update from API."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_UCR: {"ucr_id": "12345"},
                D_USER: {"user_id": "67890"},
                D_STATUS: {"status": "active"},
                D_CLUSTER: {
                    D_VEHICLE: {
                        "vehicle1": {"name": "Ambulance 1"},
                        "vehicle2": {"name": "Fire Truck 1"},
                    }
                },
                D_ALARM: {
                    "items": {
                        "alarm1": {"closed": False, "title": "Fire Alarm"},
                        "alarm2": {"closed": True, "title": "Test Alarm"},
                        "alarm3": {"closed": False, "title": "Medical Emergency"},
                    }
                },
            },
        }

        # Mock vehicle property responses
        mock_api.get_vehicle_property.side_effect = [
            {D_DATA: {"property1": "value1"}},
            {D_DATA: {"property2": "value2"}},
        ]

        result = await update_data(mock_api, cluster_data)

        # Check that data was updated
        assert result[D_UCR] == {"ucr_id": "12345"}
        assert result[D_USER] == {"user_id": "67890"}
        assert result[D_STATUS] == {"status": "active"}

        # Check that vehicle properties were added
        assert "vehicle1" in result[D_CLUSTER][D_VEHICLE]
        assert "vehicle2" in result[D_CLUSTER][D_VEHICLE]
        assert result[D_CLUSTER][D_VEHICLE]["vehicle1"]["property1"] == "value1"
        assert result[D_CLUSTER][D_VEHICLE]["vehicle2"]["property2"] == "value2"

        # Check open alarms calculation
        assert result[D_ALARM][D_OPEN_ALARMS] == 2  # alarm1 and alarm3 are not closed

    async def test_update_data_api_failure_no_success(
        self, mock_api: MagicMock
    ) -> None:
        """Test handling of API response without success flag."""
        cluster_data = {D_UCR: {"existing": "data"}}

        mock_api.get_ucr_data.return_value = {"success": False, "error": "API Error"}

        result = await update_data(mock_api, cluster_data)

        # Should return unchanged cluster_data
        assert result == cluster_data
        mock_api.get_vehicle_property.assert_not_called()

    async def test_update_data_api_exception(self, mock_api: MagicMock) -> None:
        """Test handling of API exceptions."""
        cluster_data = {D_UCR: {"existing": "data"}}

        mock_api.get_ucr_data.side_effect = ClientError("Network error")

        result = await update_data(mock_api, cluster_data)

        # Should return unchanged cluster_data
        assert result == cluster_data
        mock_api.get_vehicle_property.assert_not_called()

    async def test_update_data_converts_empty_lists_to_dicts(
        self, mock_api: MagicMock
    ) -> None:
        """Test that empty lists in API response are converted to dicts."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_USER: [],  # Empty list should become empty dict
                D_STATUS: {"status": "active"},  # Normal dict should stay
                D_CLUSTER: {
                    D_VEHICLE: []  # Nested empty list should become empty dict
                },
            },
        }

        result = await update_data(mock_api, cluster_data)

        assert result[D_USER] == {}
        assert result[D_STATUS] == {"status": "active"}
        assert result[D_CLUSTER][D_VEHICLE] == {}

    async def test_update_data_handles_missing_data_keys(
        self, mock_api: MagicMock
    ) -> None:
        """Test handling of missing keys in API response."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_UCR: {"ucr_id": "12345"}
                # Missing other keys
            },
        }

        result = await update_data(mock_api, cluster_data)

        # Existing key should be updated
        assert result[D_UCR] == {"ucr_id": "12345"}

        # Missing keys should be set to empty dicts
        assert result[D_USER] == {}
        assert result[D_STATUS] == {}

    async def test_update_data_vehicle_property_error(
        self, mock_api: MagicMock
    ) -> None:
        """Test handling of vehicle property fetch errors."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_CLUSTER: {
                    D_VEHICLE: {
                        "vehicle1": {"name": "Ambulance 1"},
                        "vehicle2": {"name": "Fire Truck 1"},
                    }
                }
            },
        }

        # First vehicle property succeeds, second fails
        mock_api.get_vehicle_property.side_effect = [
            {D_DATA: {"property1": "value1"}},
            HomeAssistantError("Property fetch failed"),
        ]

        result = await update_data(mock_api, cluster_data)

        # First vehicle should have properties
        assert result[D_CLUSTER][D_VEHICLE]["vehicle1"]["property1"] == "value1"

        # Second vehicle should still exist but without additional properties
        assert "vehicle2" in result[D_CLUSTER][D_VEHICLE]
        assert "name" in result[D_CLUSTER][D_VEHICLE]["vehicle2"]

    async def test_update_data_vehicle_property_unexpected_format(
        self, mock_api: MagicMock
    ) -> None:
        """Test handling of unexpected vehicle property format."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {D_CLUSTER: {D_VEHICLE: {"vehicle1": {"name": "Ambulance 1"}}}},
        }

        # Return non-dict data
        mock_api.get_vehicle_property.return_value = {D_DATA: "unexpected_string"}

        result = await update_data(mock_api, cluster_data)

        # Vehicle should still exist
        assert "vehicle1" in result[D_CLUSTER][D_VEHICLE]

    async def test_update_data_alarm_processing_error(
        self, mock_api: MagicMock
    ) -> None:
        """Test handling of alarm processing errors."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_ALARM: {
                    "items": "invalid_format"  # Should be dict, not string
                }
            },
        }

        result = await update_data(mock_api, cluster_data)

        # Should handle the error gracefully
        assert D_ALARM in result

    async def test_update_data_alarm_no_items(self, mock_api: MagicMock) -> None:
        """Test alarm processing when no alarm items exist."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_ALARM: {}  # No items key
            },
        }

        result = await update_data(mock_api, cluster_data)

        # Should set open_alarms to 0
        assert result[D_ALARM].get(D_OPEN_ALARMS) == 0

    async def test_update_data_alarm_empty_items(self, mock_api: MagicMock) -> None:
        """Test alarm processing with empty alarm items."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {
                D_ALARM: {
                    "items": {}  # Empty items dict
                }
            },
        }

        result = await update_data(mock_api, cluster_data)

        # Should set open_alarms to 0
        assert result[D_ALARM][D_OPEN_ALARMS] == 0

    async def test_update_data_preserves_existing_data_on_error(
        self, mock_api: MagicMock
    ) -> None:
        """Test that existing data is preserved when API call fails."""
        cluster_data = {
            D_UCR: {"existing_ucr": "data"},
            D_USER: {"existing_user": "data"},
        }

        mock_api.get_ucr_data.side_effect = ClientError("Network error")

        result = await update_data(mock_api, cluster_data)

        # Should return original data unchanged
        assert result == cluster_data

    async def test_update_data_partial_update_with_errors(
        self, mock_api: MagicMock
    ) -> None:
        """Test partial updates when some operations succeed and others fail."""
        cluster_data = {}

        mock_api.get_ucr_data.return_value = {
            "success": True,
            D_DATA: {D_UCR: {"ucr_id": "12345"}, D_USER: {"user_id": "67890"}},
        }

        # Vehicle property fetch fails
        mock_api.get_vehicle_property.side_effect = ClientError("Property error")

        result = await update_data(mock_api, cluster_data)

        # Basic data should still be updated
        assert result[D_UCR] == {"ucr_id": "12345"}
        assert result[D_USER] == {"user_id": "67890"}

        # Other keys should be initialized as empty dicts
        assert result[D_STATUS] == {}
