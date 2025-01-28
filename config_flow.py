"""Config flow for myDivera integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DiveraCredentials as dc
from .const import D_UCR, DOMAIN, MINOR_VERSION, UPDATE_INTERVAL_OPS, VERSION

LOGGER = logging.getLogger(__name__)


class MyDiveraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for myDivera integration."""

    VERSION = VERSION
    MINOR_VERSION = MINOR_VERSION

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.session = None
        self.errors: dict[str, str] = {}
        self.hubs_created: list = []
        self.hubs_existing: list = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step for user configuration."""
        self.session = async_get_clientsession(self.hass)

        if user_input is None:
            return self._show_user_form()

        self.errors, hubs, api_key = await dc.validate_login(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_api_key_form()

        return await self._process_hubs(hubs, api_key, user_input)

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the API key input step."""
        if user_input is None:
            return self._show_api_key_form()

        self.errors = {}
        self.errors, hubs, api_key = await dc.validate_api_key(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_user_form()

        return await self._process_hubs(hubs, api_key, user_input)

    def _show_user_form(self):
        """Display the user input form."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        "update_interval_alarms", default=UPDATE_INTERVAL_OPS
                    ): int,
                }
            ),
            errors=self.errors,
        )

    def _show_api_key_form(self):
        """Display the API key input form."""
        return self.async_show_form(
            step_id="api_key",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(
                        "update_interval_alarms", default=UPDATE_INTERVAL_OPS
                    ): int,
                }
            ),
            errors=self.errors,
        )

    async def _process_hubs(self, hubs, api_key, user_input):
        """Process hub creation or identify existing hubs."""
        await self._create_hubs(hubs, api_key, user_input)

        if self.hubs_created:
            return self.async_abort(
                reason="hubs_created",
                description_placeholders={"names": ", ".join(self.hubs_created)},
            )

        if self.hubs_existing:
            return self.async_abort(
                reason="hubs_existing",
                description_placeholders={"names": ", ".join(self.hubs_existing)},
            )

        return self.async_abort(reason="no_new_hubs_found")

    async def _create_hubs(self, hubs, api_key, user_input):
        """Create new hubs if they do not already exist."""
        for ucr_id, name in hubs.items():
            ucr = ucr_id.lower()
            if any(
                entry.data.get(D_UCR) == ucr or entry.data.get("name") == name
                for entry in self._async_current_entries()
            ):
                LOGGER.warning("Hub '%s' already exists, skipping creation", name)
                self.hubs_existing.append(f"\n{name}")
                continue

            new_hub = {
                D_UCR: ucr,
                "api_key": api_key,
                "update_interval_alarms": user_input["update_interval_alarms"],
                "name": name,
            }

            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": "import"}, data=new_hub
                )
            )
            self.hubs_created.append(f"\n{name}")

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle automatic creation of a hub configuration from YAML."""
        if any(
            entry.data.get(D_UCR) == import_data[D_UCR]
            for entry in self._async_current_entries()
        ):
            LOGGER.warning("Hub '%s' already configured", import_data[D_UCR])
            return self.async_abort(reason="already_configured")

        LOGGER.info("Creating hub '%s'", import_data["name"])
        return self.async_create_entry(title=import_data["name"], data=import_data)
