"""Tests for DiveraControl API client."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)

from custom_components.diveracontrol.const import (
    API_ACCESS_KEY,
    API_ALARM,
    API_MESSAGES,
    API_NEWS,
    API_PULL_ALL,
    API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    API_USING_VEHICLE_SET_SINGLE,
    BASE_API_V2_URL,
    D_UCR,
)
from custom_components.diveracontrol.divera_api import DiveraAPI


@pytest.fixture
def api_client(hass: HomeAssistant) -> Generator[DiveraAPI]:
    """Create a DiveraAPI client for testing."""
    with patch(
        "custom_components.diveracontrol.divera_api.async_get_clientsession"
    ) as mock_session:
        session = MagicMock()
        mock_session.return_value = session
        api = DiveraAPI(hass=hass, ucr_id="123456", api_key="test_api_key_123")
        yield api


class TestDiveraAPIInit:
    """Tests for DiveraAPI initialization."""

    async def test_init(self, hass: HomeAssistant) -> None:
        """Test DiveraAPI initialization."""
        api = DiveraAPI(hass=hass, ucr_id="123456", api_key="test_key")

        assert api.ucr_id == "123456"
        assert api.api_key == "test_key"
        assert api.hass == hass
        assert api.session is not None

    async def test_redact_url(self, api_client: DiveraAPI) -> None:
        """Test URL redaction for logging."""
        url = "https://api.divera247.com/v2/pull/all?accesskey=test_api_key_123&ucr=123456"
        redacted = api_client._redact_url(url)

        assert "test_api_key_123" not in redacted
        assert "***" in redacted
        assert "ucr=123456" in redacted


class TestAPIRequest:
    """Tests for api_request method."""

    async def test_successful_get_request(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True, "data": "test"})
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.session, "request") as mock_request:
            # Create async context manager mock
            mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await api_client.api_request(
                url="https://api.test.com/endpoint", method="GET"
            )

            assert result == {"success": True, "data": "test"}
            mock_request.assert_called_once()
            # Check positional arguments
            call_args = mock_request.call_args[0]
            assert call_args[0] == "GET"  # method
            # Check that timeout was set
            assert "timeout" in mock_request.call_args[1]

    async def test_request_with_parameters(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test request with URL parameters."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            await api_client.api_request(
                url="https://api.test.com/endpoint",
                method="GET",
                parameters={"custom": "value"},
            )

            # Verify URL contains api key, ucr, and custom parameter
            called_url = mock_request.call_args[0][1]
            assert API_ACCESS_KEY in called_url
            assert "test_api_key_123" in called_url
            assert D_UCR in called_url
            assert "123456" in called_url
            assert "custom=value" in called_url

    async def test_request_with_payload(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test POST request with JSON payload."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            payload = {"title": "Test", "message": "Test message"}
            await api_client.api_request(
                url="https://api.test.com/endpoint", method="POST", payload=payload
            )

            # Check positional and keyword arguments
            call_args = mock_request.call_args[0]
            call_kwargs = mock_request.call_args[1]
            assert call_args[0] == "POST"  # method is positional
            assert call_kwargs["json"] == payload

    async def test_request_with_custom_headers(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test request with custom headers."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            custom_headers = {"X-Custom": "test"}
            await api_client.api_request(
                url="https://api.test.com/endpoint",
                method="GET",
                headers=custom_headers,
            )

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"] == custom_headers

    async def test_request_auth_error_401(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test API request with 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status = 401

        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=401,
            message="Unauthorized",
        )

        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(side_effect=error)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(ConfigEntryAuthFailed) as exc_info:
                await api_client.api_request(
                    url="https://api.test.com/endpoint", method="GET"
                )

            assert "Invalid API key" in str(exc_info.value)
            assert "123456" in str(exc_info.value)

    async def test_request_server_error_500(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test API request with 500 server error."""
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
            message="Internal Server Error",
        )

        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(side_effect=error)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(ConfigEntryNotReady) as exc_info:
                await api_client.api_request(
                    url="https://api.test.com/endpoint", method="GET"
                )

            assert "Divera API unavailable" in str(exc_info.value)
            assert "500" in str(exc_info.value)

    async def test_request_timeout(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test API request timeout."""
        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(
                side_effect=TimeoutError("Connection timeout")
            )
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(ConfigEntryNotReady) as exc_info:
                await api_client.api_request(
                    url="https://api.test.com/endpoint", method="GET"
                )

            assert "Timeout connecting" in str(exc_info.value)

    async def test_request_client_error(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test API request with generic client error."""
        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(
                side_effect=ClientError("Connection failed")
            )
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(HomeAssistantError) as exc_info:
                await api_client.api_request(
                    url="https://api.test.com/endpoint", method="GET"
                )

            assert "Failed to connect to Divera API" in str(exc_info.value)

    async def test_request_other_http_error(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test API request with other HTTP error (e.g., 400, 404)."""
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        with patch.object(api_client.session, "request") as mock_request:
            mock_request.return_value.__aenter__ = AsyncMock(side_effect=error)
            mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(HomeAssistantError) as exc_info:
                await api_client.api_request(
                    url="https://api.test.com/endpoint", method="GET"
                )

            assert "Divera API error" in str(exc_info.value)
            assert "404" in str(exc_info.value)


class TestAPIEndpoints:
    """Tests for specific API endpoint methods."""

    async def test_get_ucr_data(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test get_ucr_data method."""
        expected_data = {"cluster": {"name": "Test Cluster"}, "users": []}

        with patch.object(
            api_client, "api_request", return_value=expected_data
        ) as mock_request:
            result = await api_client.get_ucr_data()

            assert result == expected_data
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert BASE_API_V2_URL in call_args[0][0]
            assert API_PULL_ALL in call_args[0][0]
            assert call_args[0][1] == "GET"

    async def test_post_vehicle_status(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_vehicle_status method."""
        vehicle_id = 789
        payload = {"status_id": 3, "fms_real": 1}

        # Mock permission check to pass
        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_vehicle_status(vehicle_id, payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_USING_VEHICLE_SET_SINGLE in call_args[0][0]
            assert str(vehicle_id) in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_post_alarms(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_alarms method."""
        payload = {"title": "Test Alarm", "priority": 1}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_alarms(payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_ALARM in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_put_alarms(self, hass: HomeAssistant, api_client: DiveraAPI) -> None:
        """Test put_alarms method."""
        alarm_id = 12345
        payload = {"title": "Updated Alarm"}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.put_alarms(alarm_id, payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_ALARM in call_args[0][0]
            assert str(alarm_id) in call_args[0][0]
            assert call_args[0][1] == "PUT"
            assert call_args[1]["payload"] == payload

    async def test_post_close_alarm(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_close_alarm method."""
        alarm_id = 12345
        payload = {"text": "Closing alarm"}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_close_alarm(payload, alarm_id)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_ALARM in call_args[0][0]
            assert "close" in call_args[0][0]
            assert str(alarm_id) in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_post_message(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_message method."""
        payload = {"title": "Test Message", "text": "Message content"}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_message(payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_MESSAGES in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_get_vehicle_property(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test get_vehicle_property method."""
        vehicle_id = 789
        expected_data = {"properties": {"water": 1000}}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(
                api_client, "api_request", return_value=expected_data
            ) as mock_request,
        ):
            result = await api_client.get_vehicle_property(vehicle_id)

            assert result == expected_data
            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_USING_VEHICLE_PROP in call_args[0][0]
            assert "get" in call_args[0][0]
            assert str(vehicle_id) in call_args[0][0]
            assert call_args[0][1] == "GET"

    async def test_post_using_vehicle_property(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_using_vehicle_property method."""
        vehicle_id = 789
        payload = {"water": 800}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_using_vehicle_property(vehicle_id, payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_USING_VEHICLE_PROP in call_args[0][0]
            assert "set" in call_args[0][0]
            assert str(vehicle_id) in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_post_using_vehicle_crew_add(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_using_vehicle_crew with 'add' mode."""
        vehicle_id = 789
        payload = {"user_ids": [1, 2, 3]}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_using_vehicle_crew(vehicle_id, "add", payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_USING_VEHICLE_CREW in call_args[0][0]
            assert "add" in call_args[0][0]
            assert str(vehicle_id) in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_post_using_vehicle_crew_remove(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_using_vehicle_crew with 'remove' mode."""
        vehicle_id = 789
        payload = {"user_ids": [1]}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_using_vehicle_crew(vehicle_id, "remove", payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "remove" in call_args[0][0]
            assert call_args[0][1] == "POST"

    async def test_post_using_vehicle_crew_reset(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_using_vehicle_crew with 'reset' mode."""
        vehicle_id = 789
        payload = {}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_using_vehicle_crew(vehicle_id, "reset", payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "reset" in call_args[0][0]
            assert call_args[0][1] == "DELETE"

    async def test_post_using_vehicle_crew_invalid_mode(
        self, hass: HomeAssistant, api_client: DiveraAPI
    ) -> None:
        """Test post_using_vehicle_crew with invalid mode raises error."""
        vehicle_id = 789
        payload = {}

        with patch("custom_components.diveracontrol.divera_api.permission_check"):
            with pytest.raises(HomeAssistantError) as exc_info:
                await api_client.post_using_vehicle_crew(
                    vehicle_id, "invalid_mode", payload
                )

            assert "Invalid mode" in str(exc_info.value)
            assert "invalid_mode" in str(exc_info.value)

    async def test_post_news(self, hass: HomeAssistant, api_client: DiveraAPI) -> None:
        """Test post_news method."""
        payload = {"title": "Important News", "text": "News content"}

        with (
            patch(
                "custom_components.diveracontrol.divera_api.permission_check"
            ) as mock_perm,
            patch.object(api_client, "api_request") as mock_request,
        ):
            await api_client.post_news(payload)

            mock_perm.assert_called_once()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert API_NEWS in call_args[0][0]
            assert call_args[0][1] == "POST"
            assert call_args[1]["payload"] == payload

    async def test_close(self, hass: HomeAssistant, api_client: DiveraAPI) -> None:
        """Test close method (currently a dummy)."""
        # Should not raise any exception
        await api_client.close()
