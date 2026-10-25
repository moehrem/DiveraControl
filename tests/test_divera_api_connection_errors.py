"""Tests for DiveraAPIClient error handling of connection failures."""

from unittest.mock import MagicMock, patch

import pytest
from aiohttp import (
    ClientConnectorCertificateError,
    ClientConnectorDNSError,
    ClientError,
    ServerDisconnectedError,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.diveracontrol.divera_api import DiveraAPIClient


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock the client session used by DiveraAPIClient."""
    session = MagicMock()
    session.request = MagicMock(side_effect=ClientError("placeholder"))
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
    mock_session.request = MagicMock(side_effect=ClientError("Connection refused"))
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
    err = ClientError("Cannot resolve host")
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


def _connector_error(cls: type, errno: int | None, strerror: str | None) -> ClientError:
    """Build an aiohttp connector error with a realistic os_error."""
    os_error = OSError(errno, strerror) if errno is not None else OSError(strerror)
    err = cls(MagicMock(host="www.divera247.com", port=443, ssl=True), os_error)
    return err


def test_describe_client_error_dns() -> None:
    """DNS connector errors include errno, strerror and a DNS hint."""
    err = _connector_error(ClientConnectorDNSError, -2, "Name or service not known")
    msg = DiveraAPIClient._describe_client_error(err)

    assert "Name or service not known" in msg
    assert "OS error -2" in msg
    assert "DNS resolution failed" in msg


def test_describe_client_error_certificate() -> None:
    """Certificate errors include the certificate hint."""
    os_error = OSError("certificate verify failed")
    err = ClientConnectorCertificateError(
        MagicMock(host="www.divera247.com", port=443, ssl=True), os_error
    )
    msg = DiveraAPIClient._describe_client_error(err)

    assert "TLS certificate rejected" in msg
    assert "certificate verify failed" in msg


def test_describe_client_error_plain_client_error() -> None:
    """Plain ClientError without os_error degrades gracefully."""
    err = ClientError("something odd happened")
    msg = DiveraAPIClient._describe_client_error(err)

    assert "something odd happened" in msg


def test_describe_client_error_empty_message() -> None:
    """An empty message falls back to the class name."""
    err = ClientError("")
    msg = DiveraAPIClient._describe_client_error(err)

    assert "ClientError" in msg


def test_describe_client_error_server_disconnected() -> None:
    """ServerDisconnectedError gets its own hint."""
    err = ServerDisconnectedError("server closed connection")
    msg = DiveraAPIClient._describe_client_error(err)

    assert "server closed connection" in msg
    assert "closed the connection unexpectedly" in msg


async def test_connection_error_message_includes_os_error_details(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """The raised HomeAssistantError contains the structured os_error info."""
    err = _connector_error(ClientConnectorDNSError, -2, "Name or service not known")
    mock_session.request = MagicMock(side_effect=err)
    client = _make_client(hass, mock_session)

    with pytest.raises(HomeAssistantError) as exc_info:
        await client._request("/v2/pullall", "GET")

    msg = str(exc_info.value)
    assert "OS error -2: Name or service not known" in msg
    assert "DNS resolution failed" in msg
