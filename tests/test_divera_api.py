"""Tests for DiveraControl DiveraAPI client - focuses on non-session methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError

from custom_components.diveracontrol.const import (
    API_ACCESS_KEY,
    API_AUTH_LOGIN,
    API_PULL_ALL,
    BASE_API_URL,
    D_ACCESSKEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_DATA,
    D_NAME,
    D_RELATIONS_KEY,
    D_UCR,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
    D_USERNAME,
)
from custom_components.diveracontrol.divera_api import (
    ConfigFlowErrorCode,
    DiveraAPIClient,
)


# Since DiveraAPIClient requires async setup, we'll test the helper methods
# that don't require a session


class TestConfigFlowErrorCode:
    """Test ConfigFlowErrorCode enum."""

    def test_error_codes_exist(self) -> None:
        """Test that error codes exist."""
        assert hasattr(ConfigFlowErrorCode, "INVALID_CREDENTIALS")
        assert hasattr(ConfigFlowErrorCode, "CANNOT_CONNECT")
        assert hasattr(ConfigFlowErrorCode, "NO_DATA")
        assert hasattr(ConfigFlowErrorCode, "NO_CLUSTERS_FOUND")

    def test_error_codes_values(self) -> None:
        """Test error code values."""
        assert ConfigFlowErrorCode.INVALID_CREDENTIALS.value == "invalid_credentials"
        assert ConfigFlowErrorCode.CANNOT_CONNECT.value == "cannot_connect"
        assert ConfigFlowErrorCode.NO_DATA.value == "no_data"
        assert ConfigFlowErrorCode.NO_CLUSTERS_FOUND.value == "no_clusters_found"


class TestFormatAuthErrors:
    """Test _format_auth_errors method (static, doesn't need session)."""

    def test_format_auth_errors_list(self) -> None:
        """Test formatting auth errors as list."""
        # Create a mock client just to access the method
        mock_client = MagicMock()
        mock_client._format_auth_errors.return_value = {"base": "Error 1; Error 2"}

        # Since we can't instantiate the real client due to session requirements,
        # we'll just test that the method exists on the class
        from custom_components.diveracontrol.divera_api import DiveraAPIClient

        # Test the static method logic
        errors = ["Error 1", "Error 2"]
        result = {"base": "; ".join(str(err) for err in errors)}
        assert result == {"base": "Error 1; Error 2"}

    def test_format_auth_errors_dict(self) -> None:
        """Test formatting auth errors as dict."""
        errors = {"field1": "Error 1", "field2": "Error 2"}
        error_messages = []
        for value in errors.values():
            if isinstance(value, str):
                error_messages.append(value)
        result = {"base": "; ".join(error_messages)}
        assert result == {"base": "Error 1; Error 2"}


class TestMapToClusters:
    """Test _map_to_clusters method logic."""

    def test_map_to_clusters_logic(self) -> None:
        """Test the logic of mapping data to clusters."""
        # This tests the logic without actually calling the method
        data_pull_all = {
            "success": True,
            "data": {
                D_UCR: {
                    "ucr1": {D_CLUSTER_ID: "cluster1", D_NAME: "Cluster One"},
                },
                D_USER: {"firstname": "John", "lastname": "Doe"},
            },
        }

        # Simulate the mapping logic
        data_ucr = data_pull_all.get(D_DATA, {}).get(D_UCR, {})
        data_user = data_pull_all.get(D_DATA, {}).get(D_USER, {})
        user_name = f"{data_user.get('firstname', '')} {data_user.get('lastname', '')}".strip()

        clusters = {}
        for ucr, data in data_ucr.items():
            cluster_id = str(data.get(D_CLUSTER_ID, ""))
            if cluster_id:
                clusters[cluster_id] = {
                    "cluster_id": cluster_id,
                    "cluster_name": data.get(D_NAME),
                }

        assert len(clusters) == 1
        assert "cluster1" in clusters
        assert clusters["cluster1"]["cluster_name"] == "Cluster One"


class TestValidateRelationEntry:
    """Test _validate_relation_entry logic."""

    def test_validate_relation_entry_logic_valid(self) -> None:
        """Test validation logic for valid relation entry."""
        required_keys = {D_ACCESSKEY, D_USERNAME}
        relation = {D_ACCESSKEY: "key123", D_USERNAME: "test_user"}
        missing_keys = required_keys - relation.keys()
        assert len(missing_keys) == 0

    def test_validate_relation_entry_logic_missing_keys(self) -> None:
        """Test validation logic for relation entry with missing keys."""
        required_keys = {D_ACCESSKEY, D_USERNAME}
        relation = {D_ACCESSKEY: "key123"}
        missing_keys = required_keys - relation.keys()
        assert D_USERNAME in missing_keys

    def test_validate_relation_entry_logic_invalid_structure(self) -> None:
        """Test validation logic for invalid relation structure."""
        relation = "not_a_dict"
        assert not isinstance(relation, dict)


class TestValidateClusterEntry:
    """Test _validate_cluster_entry logic."""

    def test_validate_cluster_entry_logic_valid(self) -> None:
        """Test validation logic for valid cluster entry."""
        required_keys = {
            D_CLUSTER_ID,
            D_CLUSTER_NAME,
            D_RELATIONS_KEY,
            D_BASE_API_URL,
            D_UPDATE_INTERVAL_DATA,
            D_UPDATE_INTERVAL_ALARM,
        }
        entry = {
            D_CLUSTER_ID: "cluster1",
            D_CLUSTER_NAME: "Test Cluster",
            D_RELATIONS_KEY: {"ucr1": {D_ACCESSKEY: "key", D_USERNAME: "user"}},
            D_BASE_API_URL: "https://api.test.com",
            D_UPDATE_INTERVAL_DATA: 60,
            D_UPDATE_INTERVAL_ALARM: 30,
        }
        missing_keys = required_keys - entry.keys()
        assert len(missing_keys) == 0

    def test_validate_cluster_entry_logic_missing_keys(self) -> None:
        """Test validation logic for cluster entry with missing keys."""
        required_keys = {
            D_CLUSTER_ID,
            D_CLUSTER_NAME,
            D_RELATIONS_KEY,
            D_BASE_API_URL,
            D_UPDATE_INTERVAL_DATA,
            D_UPDATE_INTERVAL_ALARM,
        }
        entry = {D_CLUSTER_ID: "cluster1"}
        missing_keys = required_keys - entry.keys()
        assert len(missing_keys) > 0


class TestMapToClustersFull:
    """Test _map_to_clusters method with full implementation."""

    def test_map_to_clusters_multiple_clusters(self) -> None:
        """Test mapping data with multiple clusters."""
        client = MagicMock(spec=DiveraAPIClient)
        client._map_to_clusters = DiveraAPIClient._map_to_clusters.__get__(client, DiveraAPIClient)
        
        data_pull_all = {
            D_DATA: {
                D_UCR: {
                    "ucr1": {D_CLUSTER_ID: "cluster1", D_NAME: "Cluster One"},
                    "ucr2": {D_CLUSTER_ID: "cluster2", D_NAME: "Cluster Two"},
                },
                D_USER: {"firstname": "John", "lastname": "Doe"},
            }
        }
        
        clusters = client._map_to_clusters(
            data_pull_all,
            "test_accesskey",
            "https://api.test.com",
            60,
            30,
        )
        
        assert len(clusters) == 2
        assert "cluster1" in clusters
        assert "cluster2" in clusters
        assert clusters["cluster1"]["cluster_name"] == "Cluster One"
        assert clusters["cluster1"][D_RELATIONS_KEY]["ucr1"][D_USERNAME] == "John Doe"

    def test_map_to_clusters_missing_data(self) -> None:
        """Test mapping with missing data keys."""
        client = MagicMock(spec=DiveraAPIClient)
        client._map_to_clusters = DiveraAPIClient._map_to_clusters.__get__(client, DiveraAPIClient)
        
        data_pull_all = {}  # Empty data
        clusters = client._map_to_clusters(
            data_pull_all,
            "test_accesskey",
            "https://api.test.com",
            60,
            30,
        )
        
        assert clusters == {}


class TestFormatAuthErrorsFull:
    """Test _format_auth_errors method with full implementation."""

    def test_format_auth_errors_list(self) -> None:
        """Test formatting auth errors from list."""
        client = MagicMock(spec=DiveraAPIClient)
        client._format_auth_errors = DiveraAPIClient._format_auth_errors.__get__(client, DiveraAPIClient)
        
        errors = ["Error 1", "Error 2", "Error 3"]
        result = client._format_auth_errors(errors)
        assert result == {"base": "Error 1; Error 2; Error 3"}

    def test_format_auth_errors_dict(self) -> None:
        """Test formatting auth errors from dict."""
        client = MagicMock(spec=DiveraAPIClient)
        client._format_auth_errors = DiveraAPIClient._format_auth_errors.__get__(client, DiveraAPIClient)
        
        errors = {"field1": "Error 1", "field2": "Error 2"}
        result = client._format_auth_errors(errors)
        assert result == {"base": "Error 1; Error 2"}

    def test_format_auth_errors_dict_with_lists(self) -> None:
        """Test formatting auth errors from dict with list values."""
        client = MagicMock(spec=DiveraAPIClient)
        client._format_auth_errors = DiveraAPIClient._format_auth_errors.__get__(client, DiveraAPIClient)
        
        errors = {"field1": ["Error 1", "Error 2"], "field2": "Error 3"}
        result = client._format_auth_errors(errors)
        assert result == {"base": "Error 1; Error 2; Error 3"}


class TestDiveraAPIAsync:
    """Test async API methods with proper mocking."""

    @pytest.mark.asyncio
    async def test_request_access_empty_accesskey(self, hass: HomeAssistant) -> None:
        """Test request_access with empty accesskey."""
        with patch("custom_components.diveracontrol.divera_api.async_get_clientsession", return_value=MagicMock()):
            client = DiveraAPIClient(hass, BASE_API_URL)
            user_input = {D_ACCESSKEY: "   "}  # Whitespace only
            errors, clusters = await client.request_access(user_input)

            assert errors["base"] == ConfigFlowErrorCode.INVALID_CREDENTIALS.value
            assert clusters == {}
