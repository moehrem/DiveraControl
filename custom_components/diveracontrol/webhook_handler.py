"""Webhook handler for DiveraControl config flow."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.webhook import async_generate_id
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import D_USE_WEBHOOKS, D_WEBHOOK_ID

if TYPE_CHECKING:
    from .config_flow import DiveraControlConfigFlow

LOGGER = logging.getLogger(__name__)


class WebhookHandler:
    """Handles webhook setup for DiveraControl config flow."""

    def __init__(self, config_flow: "DiveraControlConfigFlow") -> None:
        """Initialize the webhook handler.

        Args:
            config_flow: The parent config flow instance.

        """

        self.config_flow = config_flow
        self.hass = config_flow.hass
        self.webhook_id: Any | None = None
        self.webhook_url: str = ""

    async def prepare_webhook_entry(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Prepare webhook setup for a new entry.

        Creates a webhook ID if not already present, reads the external URL, and updates the config flow entry data accordingly.
        "External URL" might be a cloud URL or an externally accessible URL configured in Home Assistant. If no URL is available, it handles the error and updates the config flow state.

        Args:
            entry_data: The entry data to prepare.

        Returns:
            ConfigFlowResult: The result of the webhook preparation.

        """

        self.config_flow.final_entry = entry_data

        try:
            self.webhook_id = self.config_flow.final_entry.get(D_WEBHOOK_ID, None)

            if self.webhook_id is None:
                self.webhook_id = async_generate_id()

            self.config_flow.final_entry[D_WEBHOOK_ID] = self.webhook_id

            self._read_url()
            return await self.config_flow.async_step_webhook_info()

        except NoURLAvailableError:
            LOGGER.error("No external URL configured for webhooks")
            self.config_flow.errors["base"] = "no_external_url"
            self.config_flow.final_entry[D_USE_WEBHOOKS] = False
            self.config_flow.final_entry.pop(D_WEBHOOK_ID, None)
            return await self.config_flow.async_step_webhook_error()

    def _read_url(self) -> None:
        """Read the external URL from Home Assistant for webhook setup.

        Raises:
            NoURLAvailableError: If no external URL is configured.

        """

        # First, check for cloud URL, then fall back to the external URL.
        # if no cloud or external URL is available, raise an error to inform the user
        # to set up an external URL for webhooks
        for allow_cloud, prefer_cloud in ((True, True), (False, False)):
            try:
                base_url = get_url(
                    self.hass,
                    allow_internal=False,
                    allow_cloud=allow_cloud,
                    prefer_cloud=prefer_cloud,
                ).rstrip("/")
            except NoURLAvailableError:
                continue
            else:
                self.webhook_url = f"{base_url}/api/webhook/{self.webhook_id}"
                return

        raise NoURLAvailableError(
            "No cloud connection or external URL configured for webhooks"
        )
