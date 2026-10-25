"""Tests for DiveraAPIClient error handling of connection failures."""

from unittest.mock import MagicMock, patch

import pytest
from aiohttp import ClientConnectionError, ClientError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.diveracontrol.divera_api import DiveraAPIClient


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock the client session used by DiveraAPIClient."""
    session = MagicMock()
    session.request = MagicMock(side_effect=ClientConnectionError("placeholder"))
    with patch(
        "custom_components.diveracontrol.divera_api.async_get_clientsession",
        return_value=session,
    ):
        yield session


def _make_client(hass: HomeAssistant, session: MagicMock) -> DiveraAPIClient:
    """Create a DiveraAPIClient bound to the mocked session."""
    client = DiveraAPIClient(hass, "https://www.divera247.com/api", timeout=1)
    client._session = session
    return client


async def test_connection_error_includes_url_and_cause(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """ClientError without request_info still reports the built URL and cause."""
    mock_session.request = MagicMock(
        side_effect=ClientConnectionError("Connection refused")
    )
    client = _make_client(hass, mock_session)

    with pytest.raises(HomeAssistantError) as exc_info:
        await client._request("/v2/pullall", "GET", params={"accesskey": "secret"})

    msg = str(exc_info.value)
    assert "Failed to connect to Divera API" in msg
    assert "GET https://www.divera247.com/api/v2/pullall" in msg
    assert "secret" not in msg
    assert "Connection refused" in msg


async def test_connection_error_uses_request_info_url(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """When request_info is available, its URL is used and redacted."""
    err = ClientConnectionError("Cannot resolve host")
    err.request_info = MagicMock()
    err.request_info.real_url = "https://www.divera247.com/api/v2/pullall?accesskey=x"
    mock_session.request = MagicMock(side_effect=err)
    client = _make_client(hass, mock_session)

    with pytest.raises(HomeAssistantError) as exc_info:
        await client._request("/v2/pullall", "GET")

    msg = str(exc_info.value)
    assert "GET https://www.divera247.com/api/v2/pullall" in msg
    assert "Cannot resolve host" in msg
    assert "accesskey=x" not in msg


async def test_connection_error_never_reports_unknown_url(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """The URL placeholder 'unknown' must no longer appear in the message."""
    mock_session.request = MagicMock(side_effect=ClientError("ssl handshake failed"))
    client = _make_client(hass, mock_session)

    with pytest.raises(HomeAssistantError) as exc_info:
        await client._request("/v2/pullall", "POST")

    msg = str(exc_info.value)
    assert "URL: unknown" not in msg
    assert "ssl handshake failed" in msg
