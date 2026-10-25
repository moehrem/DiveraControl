"""Tests for DiveraAPIClient error handling of connection failures."""

from unittest.mock import AsyncMock, MagicMock, patch

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

    err = exc_info.value
    assert err.translation_domain == "diveracontrol"
    assert err.translation_key == "api_connect_failed"
    placeholders = err.translation_placeholders
    assert placeholders["method"] == "GET"
    assert (
        placeholders["url"]
        == "https://www.divera247.com/api/v2/pullall?accesskey=%2A%2A%2A"
    )
    assert "secret" not in placeholders["url"]
    assert "Connection refused" in placeholders["details"]


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

    placeholders = exc_info.value.translation_placeholders
    assert placeholders["url"].startswith("https://www.divera247.com/api/v2/pullall")
    assert "Cannot resolve host" in placeholders["details"]
    assert "accesskey=x" not in placeholders["url"]


async def test_connection_error_never_reports_unknown_url(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """The URL placeholder 'unknown' must no longer appear in the message."""
    mock_session.request = MagicMock(side_effect=ClientError("ssl handshake failed"))
    client = _make_client(hass, mock_session)

    with pytest.raises(HomeAssistantError) as exc_info:
        await client._request("/v2/pullall", "POST")

    placeholders = exc_info.value.translation_placeholders
    assert placeholders["url"].startswith("https://www.divera247.com/api/v2/pullall")
    assert "ssl handshake failed" in placeholders["details"]


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

    placeholders = exc_info.value.translation_placeholders
    assert "OS error -2: Name or service not known" in placeholders["details"]
    assert "DNS resolution failed" in placeholders["details"]


async def test_request_retries_transient_server_error(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """5xx responses are retried and succeed on a later attempt."""
    from aiohttp import ClientResponseError, RequestInfo

    call_count = {"n": 0}

    ok = MagicMock()
    ok.status = 200
    ok.json = AsyncMock(return_value={"success": True})
    ok.raise_for_status = MagicMock()

    class FakeCtx:
        def __init__(self, response):
            self._response = response

        async def __aenter__(self):
            return self._response

        async def __aexit__(self, *exc):
            return False

    err = ClientResponseError(
        RequestInfo("https://www.divera247.com/api/v2/pullall", "GET", {}),
        (),
        status=503,
        message="Service Unavailable",
    )

    class ErrCtx:
        async def __aenter__(self):
            raise err

        async def __aexit__(self, *exc):
            return False

    def fake_request(*args, **kwargs):
        call_count["n"] += 1
        return ErrCtx() if call_count["n"] == 1 else FakeCtx(ok)

    mock_session.request = fake_request
    client = _make_client(hass, mock_session)
    client._max_retries = 2

    data = await client._request("/v2/pullall", "GET")
    assert data == {"success": True}
    assert call_count["n"] == 2


async def test_request_maps_timeout_to_not_ready(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """Timeout after all retries raises ConfigEntryNotReady with URL hint."""

    from homeassistant.exceptions import ConfigEntryNotReady

    mock_session.request = MagicMock(side_effect=TimeoutError())
    client = _make_client(hass, mock_session)
    client._max_retries = 1

    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await client._request("/v2/pullall", "GET")

    err = exc_info.value
    assert err.translation_key == "api_timeout"
    placeholders = err.translation_placeholders
    assert placeholders["method"] == "GET"
    assert placeholders["url"].startswith("https://www.divera247.com/api/v2/pullall")
    assert placeholders["attempts"] == "2"


async def test_request_maps_5xx_to_not_ready(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """Persistent 5xx after retries raises ConfigEntryNotReady."""
    from aiohttp import ClientResponseError, RequestInfo
    from homeassistant.exceptions import ConfigEntryNotReady

    err = ClientResponseError(
        RequestInfo("https://www.divera247.com/api/v2/pullall", "GET", {}),
        (),
        status=500,
        message="Internal Server Error",
    )
    mock_session.request = MagicMock(side_effect=err)
    client = _make_client(hass, mock_session)
    client._max_retries = 1

    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await client._request("/v2/pullall", "GET")

    err = exc_info.value
    assert err.translation_key == "api_unavailable"
    assert err.translation_placeholders["status"] == "500"


async def test_request_maps_401_to_auth_failed(
    hass: HomeAssistant, mock_session: MagicMock
) -> None:
    """401 is not retried and raises ConfigEntryAuthFailed."""
    from aiohttp import ClientResponseError, RequestInfo
    from homeassistant.exceptions import ConfigEntryAuthFailed

    err = ClientResponseError(
        RequestInfo("https://www.divera247.com/api/v2/pullall", "GET", {}),
        (),
        status=401,
        message="Unauthorized",
    )
    mock_session.request = MagicMock(side_effect=err)
    client = _make_client(hass, mock_session)
    client._max_retries = 2

    with pytest.raises(ConfigEntryAuthFailed) as exc_info:
        await client._request("/v2/pullall", "GET")

    err = exc_info.value
    assert err.translation_key == "api_invalid_credentials"
    assert err.translation_placeholders["status"] == "401"
    assert mock_session.request.call_count == 1
