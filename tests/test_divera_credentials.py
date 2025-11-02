"""Tests for DiveraControl divera_credentials.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientError, ClientSession

from custom_components.diveracontrol.const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_DATA,
    D_NAME,
    D_UCR,
    D_UCR_ID,
    D_USERGROUP_ID,
    BASE_API_URL,
)
from custom_components.diveracontrol.divera_credentials import DiveraCredentials


class TestValidateLogin:
    """Test the validate_login method."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock session."""
        return MagicMock(spec=ClientSession)

    async def test_validate_login_success(self, mock_session: MagicMock) -> None:
        """Test successful login validation."""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "user": {"access_token": "test_api_key"},
                "ucr": [
                    {"id": 123, "name": "Test Cluster", "usergroup_id": "group1"},
                    {"id": 456, "name": "Another Cluster", "usergroup_id": "group2"},
                ],
            },
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {}
        assert len(clusters) == 2
        assert clusters["123"] == {
            D_CLUSTER_NAME: "Test Cluster",
            D_UCR_ID: "123",
            D_API_KEY: "test_api_key",
            D_USERGROUP_ID: "group1",
        }
        assert clusters["456"] == {
            D_CLUSTER_NAME: "Another Cluster",
            D_UCR_ID: "456",
            D_API_KEY: "test_api_key",
            D_USERGROUP_ID: "group2",
        }

    async def test_validate_login_auth_failure(self, mock_session: MagicMock) -> None:
        """Test login validation with authentication failure."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "success": False,
            "errors": {"username": "Invalid username"},
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "wrong", "password": "wrong"}, BASE_API_URL
        )

        assert errors == {"base": "Invalid username"}
        assert clusters == {}

    async def test_validate_login_connection_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test login validation with connection error."""
        mock_session.post.side_effect = ClientError("Connection failed")

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {"base": "cannot_connect"}
        assert clusters == {}

    async def test_validate_login_timeout_error(self, mock_session: MagicMock) -> None:
        """Test login validation with timeout error."""
        mock_session.post.side_effect = TimeoutError("Request timed out")

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {"base": "cannot_connect"}
        assert clusters == {}

    async def test_validate_login_data_parsing_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test login validation with data parsing error."""
        mock_response = AsyncMock()
        mock_response.json.side_effect = TypeError("Invalid JSON")
        mock_session.post.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {"base": "no_data"}
        assert clusters == {}

    async def test_validate_login_unexpected_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test login validation with unexpected error."""
        mock_session.post.side_effect = Exception("Unexpected error")

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {"base": "unknown"}
        assert clusters == {}

    async def test_validate_login_empty_ucr_data(self, mock_session: MagicMock) -> None:
        """Test login validation with empty UCR data."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"user": {"access_token": "test_api_key"}, "ucr": []},
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {}
        assert clusters == {}

    async def test_validate_login_missing_ucr_id(self, mock_session: MagicMock) -> None:
        """Test login validation with missing UCR ID."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "user": {"access_token": "test_api_key"},
                "ucr": [
                    {
                        "name": "Test Cluster",
                        "usergroup_id": "group1",
                        # Missing "id" field
                    }
                ],
            },
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_login(
            {}, mock_session, {"username": "test", "password": "test"}, BASE_API_URL
        )

        assert errors == {}
        assert clusters == {}  # Should not include cluster without ID


class TestValidateApiKey:
    """Test the validate_api_key method."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock session."""
        return MagicMock(spec=ClientSession)

    async def test_validate_api_key_success(self, mock_session: MagicMock) -> None:
        """Test successful API key validation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            D_DATA: {
                D_UCR: {
                    "123": {D_NAME: "Test Cluster", D_USERGROUP_ID: "group1"},
                    "456": {D_NAME: "Another Cluster", D_USERGROUP_ID: "group2"},
                }
            }
        }
        mock_session.request.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_api_key(
            {}, mock_session, {"api_key": "test_key"}, BASE_API_URL
        )

        assert errors == {}
        assert len(clusters) == 2
        assert clusters["123"] == {
            D_CLUSTER_NAME: "Test Cluster",
            D_UCR_ID: "123",
            D_API_KEY: "test_key",
            D_USERGROUP_ID: "group1",
        }
        assert clusters["456"] == {
            D_CLUSTER_NAME: "Another Cluster",
            D_UCR_ID: "456",
            D_API_KEY: "test_key",
            D_USERGROUP_ID: "group2",
        }

    async def test_validate_api_key_http_error(self, mock_session: MagicMock) -> None:
        """Test API key validation with HTTP error."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_session.request.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_api_key(
            {}, mock_session, {"api_key": "invalid_key"}, BASE_API_URL
        )

        assert errors == {"base": "Invalid API key"}
        assert clusters == {}

    async def test_validate_api_key_connection_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test API key validation with connection error."""
        mock_session.request.side_effect = ClientError("Connection failed")

        errors, clusters = await DiveraCredentials.validate_api_key(
            {}, mock_session, {"api_key": "test_key"}, BASE_API_URL
        )

        assert errors == {"base": "cannot_connect"}
        assert clusters == {}

    async def test_validate_api_key_timeout_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test API key validation with timeout error."""
        mock_session.request.side_effect = TimeoutError("Request timed out")

        errors, clusters = await DiveraCredentials.validate_api_key(
            {}, mock_session, {"api_key": "test_key"}, BASE_API_URL
        )

        assert errors == {"base": "cannot_connect"}
        assert clusters == {}

    async def test_validate_api_key_data_parsing_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test API key validation with data parsing error."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.side_effect = TypeError("Invalid JSON")
        mock_session.request.return_value.__aenter__.return_value = mock_response

        errors, clusters = await DiveraCredentials.validate_api_key(
            {}, mock_session, {"api_key": "test_key"}, BASE_API_URL
        )

        assert errors == {"base": "no_data"}
        assert clusters == {}

    async def test_validate_api_key_unexpected_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test API key validation with unexpected error."""
        mock_session.request.side_effect = Exception("Unexpected error")

        errors, clusters = await DiveraCredentials.validate_api_key(
            {}, mock_session, {"api_key": "test_key"}, BASE_API_URL
        )

        assert errors == {"base": "Unexpected error"}
        assert clusters == {}


class TestFormatAuthErrors:
    """Test the _format_auth_errors method."""

    def test_format_auth_errors_list(self) -> None:
        """Test formatting list of errors."""
        raw_errors = ["Error 1", "Error 2", "Error 3"]
        result = DiveraCredentials._format_auth_errors(raw_errors)
        assert result == {"base": "Error 1; Error 2; Error 3"}

    def test_format_auth_errors_dict_strings(self) -> None:
        """Test formatting dict with string values."""
        raw_errors = {"field1": "Error 1", "field2": "Error 2"}
        result = DiveraCredentials._format_auth_errors(raw_errors)
        assert result == {"base": "Error 1; Error 2"}

    def test_format_auth_errors_dict_lists(self) -> None:
        """Test formatting dict with list values."""
        raw_errors = {"field1": ["Error 1", "Error 2"], "field2": "Error 3"}
        result = DiveraCredentials._format_auth_errors(raw_errors)
        assert result == {"base": "Error 1; Error 2; Error 3"}

    def test_format_auth_errors_dict_mixed(self) -> None:
        """Test formatting dict with mixed value types."""
        raw_errors = {"field1": "Error 1", "field2": ["Error 2", 123], "field3": None}
        result = DiveraCredentials._format_auth_errors(raw_errors)
        assert result == {"base": "Error 1; Error 2; 123; None"}

    def test_format_auth_errors_string(self) -> None:
        """Test formatting string error."""
        raw_errors = "Single error message"
        result = DiveraCredentials._format_auth_errors(raw_errors)
        assert result == {"base": "Single error message"}

    def test_format_auth_errors_other_type(self) -> None:
        """Test formatting other types (converted to string)."""
        raw_errors = 123
        result = DiveraCredentials._format_auth_errors(raw_errors)
        assert result == {"base": "123"}
