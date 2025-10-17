"""Fixtures for DiveraControl integration tests."""

from collections.abc import Generator
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol.const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_NAME,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERGROUP_ID,
    DOMAIN,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


def load_fixture(filename: str) -> dict:
    """Load a fixture JSON file and return parsed data."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with fixture_path.open(encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture
def api_post_auth_single_ucr() -> dict:
    """Load auth response with single UCR."""
    return load_fixture("api_post_auth_single_ucr.json")


@pytest.fixture
def api_post_auth_multi_ucr() -> dict:
    """Load auth response with multiple UCRs."""
    return load_fixture("api_post_auth_multi_ucr.json")


@pytest.fixture
def api_post_auth_invalid() -> dict:
    """Load invalid auth response."""
    return load_fixture("api_post_auth_invalid.json")


@pytest.fixture
def api_get_pull_all_response() -> dict:
    """Load api_get_pull_all.json fixture containing cluster data."""
    return load_fixture("api_get_pull_all.json")


@pytest.fixture
def api_validation_clusters(api_post_auth_single_ucr: dict) -> dict:
    """Extract and format cluster data from authentication response."""
    clusters = {}
    data_user = api_post_auth_single_ucr.get("data", {}).get("user", {})
    api_key = data_user.get("accesskey", "")
    data_ucr = api_post_auth_single_ucr.get("data", {}).get("ucr", {})

    for cluster in data_ucr:
        ucr_id = str(cluster.get("id", ""))
        clusters[ucr_id] = {
            D_CLUSTER_NAME: cluster.get(D_NAME, ""),
            D_UCR_ID: ucr_id,
            D_API_KEY: api_key,
            D_USERGROUP_ID: cluster.get(D_USERGROUP_ID, ""),
        }

    return clusters


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Löschzug Musterstadt",
        data={
            D_UCR_ID: "123456",
            D_CLUSTER_NAME: "Löschzug Musterstadt",
            D_API_KEY: "test_api_key_123456",
            D_UPDATE_INTERVAL_DATA: UPDATE_INTERVAL_DATA,
            D_UPDATE_INTERVAL_ALARM: UPDATE_INTERVAL_ALARM,
        },
        unique_id="123456",
    )


@pytest.fixture
def user_input_login() -> dict:
    """Return valid user input for login config flow step."""
    return {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "correct_password",
        D_UPDATE_INTERVAL_DATA: 60,
        D_UPDATE_INTERVAL_ALARM: 30,
    }


@pytest.fixture
def user_input_api_key() -> dict:
    """Return valid user input for API key config flow step."""
    return {
        D_API_KEY: "test_api_key_123456",
        D_UPDATE_INTERVAL_DATA: 60,
        D_UPDATE_INTERVAL_ALARM: 30,
    }


@pytest.fixture
def mock_divera_credentials_base() -> Generator[tuple[MagicMock, MagicMock]]:
    """Mock aiohttp ClientSession methods and return mocks for customization."""

    with (
        patch(
            "custom_components.diveracontrol.divera_credentials.ClientSession.post"
        ) as mock_post,
        patch(
            "custom_components.diveracontrol.divera_credentials.ClientSession.request"
        ) as mock_request,
    ):
        yield mock_post, mock_request


@pytest.fixture
def mock_divera_credentials(
    mock_divera_credentials_base: tuple[MagicMock, MagicMock],
    api_post_auth_single_ucr: dict,
    api_post_auth_invalid: dict,
    api_get_pull_all_response: dict,
) -> None:
    """Mock aiohttp responses with single UCR (default scenario)."""
    mock_post, mock_request = mock_divera_credentials_base

    def create_post_context(*args, **kwargs):
        """Create mock POST context manager - MUST be synchronous."""
        request_json = kwargs.get("json", {})
        login_data = request_json.get("Login", {})

        mock_response = MagicMock()

        if (
            login_data.get("username") == "test@example.com"
            and login_data.get("password") == "correct_password"
        ):
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=api_post_auth_single_ucr)
        else:
            mock_response.status = 401
            mock_response.json = AsyncMock(return_value=api_post_auth_invalid)

        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        return context_manager

    mock_post.side_effect = create_post_context

    def create_request_context(*args, **kwargs):
        """Create mock REQUEST context manager - MUST be synchronous."""
        url = kwargs.get("url", "")

        mock_response = MagicMock()

        if "test_api_key_123456" in url:
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=api_get_pull_all_response)
        else:
            mock_response.status = 401
            mock_response.json = AsyncMock(
                return_value={"success": False, "message": "Invalid API key"}
            )

        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        return context_manager

    mock_request.side_effect = create_request_context


@pytest.fixture
def mock_divera_credentials_multi_ucr(
    mock_divera_credentials_base: tuple[MagicMock, MagicMock],
    api_post_auth_multi_ucr: dict,
    api_post_auth_invalid: dict,
    api_get_pull_all_response: dict,
) -> None:
    """Mock aiohttp responses with multiple UCRs."""
    mock_post, mock_request = mock_divera_credentials_base

    def create_post_context(*args, **kwargs):
        """Create mock POST context manager."""
        request_json = kwargs.get("json", {})
        login_data = request_json.get("Login", {})

        mock_response = MagicMock()

        if (
            login_data.get("username") == "test@example.com"
            and login_data.get("password") == "correct_password"
        ):
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=api_post_auth_multi_ucr)
        else:
            mock_response.status = 401
            mock_response.json = AsyncMock(return_value=api_post_auth_invalid)

        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        return context_manager

    mock_post.side_effect = create_post_context

    def create_request_context(*args, **kwargs):
        """Create mock REQUEST context manager."""
        url = kwargs.get("url", "")

        mock_response = MagicMock()

        if "test_api_key_123456" in url:
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=api_get_pull_all_response)
        else:
            mock_response.status = 403
            mock_response.json = AsyncMock(
                return_value={"success": False, "message": "Invalid API key"}
            )

        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        return context_manager

    mock_request.side_effect = create_request_context


@pytest.fixture
def mock_divera_api(api_get_pull_all_response: dict) -> Generator[None]:
    """Mock DiveraAPI class for integration tests."""
    with patch("custom_components.diveracontrol.DiveraAPI") as mock_api_class:
        api_instance = MagicMock()

        api_instance.get_ucr_data = AsyncMock(
            return_value=api_get_pull_all_response.get("data", {})
        )
        api_instance.close = AsyncMock()

        mock_api_class.return_value = api_instance
        yield


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_divera_api,
) -> MockConfigEntry:
    """Set up the DiveraControl integration for testing."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
