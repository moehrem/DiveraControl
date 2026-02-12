"""Webhook handlers for DiveraControl."""

from __future__ import annotations

from http import HTTPStatus
import logging

from aiohttp.web import Request, Response

from homeassistant.core import HomeAssistant

from .const import D_WEBHOOK_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: Request,
) -> Response:
    """Handle incoming Divera webhooks."""
    _LOGGER.debug("Received webhook %s", webhook_id)

    entry = next(
        (
            config_entry
            for config_entry in hass.config_entries.async_entries(DOMAIN)
            if config_entry.data.get(D_WEBHOOK_ID) == webhook_id
        ),
        None,
    )

    if entry is None:
        _LOGGER.warning("Webhook %s did not match any config entry", webhook_id)
        return Response(status=HTTPStatus.OK)

    coordinator = entry.runtime_data
    await coordinator.async_request_refresh()

    return Response(status=HTTPStatus.OK)
