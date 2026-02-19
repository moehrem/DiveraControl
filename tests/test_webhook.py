"""Tests for webhook handling."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp.web import Response
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.diveracontrol.const import (
    D_CLUSTER_NAME,
    D_USE_WEBHOOKS,
    D_WEBHOOK_ID,
    DOMAIN,
)
from custom_components.diveracontrol.webhook import async_handle_webhook
from custom_components.diveracontrol.webhook_handler import WebhookHandler


async def test_async_handle_webhook_matches_entry(hass: HomeAssistant) -> None:
    """Test webhook refreshes coordinator when webhook ID matches an entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            D_CLUSTER_NAME: "Test Cluster",
            D_WEBHOOK_ID: "known_webhook",
        },
    )
    config_entry.runtime_data = MagicMock()
    config_entry.runtime_data.async_request_refresh = AsyncMock()
    config_entry.add_to_hass(hass)

    response = await async_handle_webhook(
        hass,
        "known_webhook",
        MagicMock(),
    )

    assert isinstance(response, Response)
    assert response.status == 200
    config_entry.runtime_data.async_request_refresh.assert_awaited_once()


async def test_async_handle_webhook_unknown_id(hass: HomeAssistant) -> None:
    """Test unknown webhook ID returns 200 and does not refresh any coordinator."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            D_CLUSTER_NAME: "Test Cluster",
            D_WEBHOOK_ID: "known_webhook",
        },
    )
    config_entry.runtime_data = MagicMock()
    config_entry.runtime_data.async_request_refresh = AsyncMock()
    config_entry.add_to_hass(hass)

    response = await async_handle_webhook(
        hass,
        "unknown_webhook",
        MagicMock(),
    )

    assert isinstance(response, Response)
    assert response.status == 200
    config_entry.runtime_data.async_request_refresh.assert_not_awaited()


async def test_prepare_webhook_entry_success(hass: HomeAssistant) -> None:
    """Test webhook preparation creates ID and shows webhook info on success."""
    config_flow = MagicMock()
    config_flow.hass = hass
    config_flow.final_entry = None
    config_flow.errors = {}
    config_flow.async_step_webhook_info = AsyncMock(return_value={"type": "form"})

    handler = WebhookHandler(config_flow)
    config_flow.webhook_handler = handler

    with (
        patch(
            "custom_components.diveracontrol.webhook_handler.async_generate_id",
            return_value="generated_webhook_id",
        ),
        patch(
            "custom_components.diveracontrol.webhook_handler.get_url",
            return_value="https://example.duckdns.org",
        ),
    ):
        result = await handler.prepare_webhook_entry({D_USE_WEBHOOKS: True})

    assert result == {"type": "form"}
    assert config_flow.final_entry[D_WEBHOOK_ID] == "generated_webhook_id"
    assert (
        handler.webhook_url
        == "https://example.duckdns.org/api/webhook/generated_webhook_id"
    )
    config_flow.async_step_webhook_info.assert_awaited_once()


async def test_prepare_webhook_entry_no_external_url(hass: HomeAssistant) -> None:
    """Test webhook preparation handles missing external URL gracefully."""
    config_flow = MagicMock()
    config_flow.hass = hass
    config_flow.final_entry = None
    config_flow.errors = {}
    config_flow.async_step_webhook_error = AsyncMock(return_value={"type": "form"})

    handler = WebhookHandler(config_flow)
    config_flow.webhook_handler = handler

    with (
        patch(
            "custom_components.diveracontrol.webhook_handler.async_generate_id",
            return_value="generated_webhook_id",
        ),
        patch(
            "custom_components.diveracontrol.webhook_handler.get_url",
            side_effect=NoURLAvailableError,
        ),
    ):
        result = await handler.prepare_webhook_entry({D_USE_WEBHOOKS: True})

    assert result == {"type": "form"}
    assert config_flow.errors == {"base": "no_external_url"}
    assert config_flow.final_entry[D_USE_WEBHOOKS] is False
    assert D_WEBHOOK_ID not in config_flow.final_entry
    config_flow.async_step_webhook_error.assert_awaited_once()
