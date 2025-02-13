"""Config flow for myDivera integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.device_registry import async_get as async_get_device_registry


from .api import DiveraCredentials as dc
from .const import (
    D_UCR_ID,
    D_CLUSTER_ID,
    DOMAIN,
    MINOR_VERSION,
    UPDATE_INTERVAL_DATA,
    UPDATE_INTERVAL_ALARM,
    VERSION,
    PATCH_VERSION,
    D_API_KEY,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERNAME,
)

LOGGER = logging.getLogger(__name__)


class MyDiveraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for myDivera integration."""

    VERSION = VERSION
    MINOR_VERSION = MINOR_VERSION
    PATCH_VERSION = PATCH_VERSION

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.session = None
        self.errors: dict[str, str] = {}
        self.new_data: list = []
        self.existing_data: list = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step for user configuration."""
        self.session = async_get_clientsession(self.hass)

        if user_input is None:
            return self._show_user_form()

        self.errors, clusters = await dc.validate_login(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_api_key_form()

        return await self._process_hubs(clusters, user_input)

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the API key input step."""
        if user_input is None:
            return self._show_api_key_form()

        self.errors = {}
        self.errors, clusters = await dc.validate_api_key(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_user_form()

        return await self._process_hubs(clusters, user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing hub."""

        entry_id = self.context.get("entry_id")
        if not entry_id:
            return self.async_abort(reason="missing_entry_id")

        existing_entry = self.hass.config_entries.async_get_entry(entry_id)
        if not existing_entry:
            return self.async_abort(reason="hub_not_found")

        if user_input is not None:
            # new_api_key = user_input[D_API_KEY]
            new_interval_data = user_input[D_UPDATE_INTERVAL_DATA]
            new_interval_alarm = user_input[D_UPDATE_INTERVAL_ALARM]

            new_data = {
                **existing_entry.data,
                # D_API_KEY: new_api_key,
                D_UPDATE_INTERVAL_DATA: new_interval_data,
                D_UPDATE_INTERVAL_ALARM: new_interval_alarm,
            }

            return self.async_update_reload_and_abort(
                existing_entry,
                data_updates=new_data,
            )

        current_interval_data = existing_entry.data.get(D_UPDATE_INTERVAL_DATA)
        current_interval_alarm = existing_entry.data.get(D_UPDATE_INTERVAL_ALARM)

        return self._show_reconfigure_form(
            current_interval_data, current_interval_alarm
        )

    def _show_user_form(self):
        """Display the user input form."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(
                    D_UPDATE_INTERVAL_DATA, default=UPDATE_INTERVAL_DATA
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
                vol.Required(
                    D_UPDATE_INTERVAL_ALARM, default=UPDATE_INTERVAL_ALARM
                ): vol.All(vol.Coerce(int), vol.Range(min=10)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=self.errors,
        )

    def _show_api_key_form(self):
        """Display the API key input form."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    D_UPDATE_INTERVAL_DATA, default=UPDATE_INTERVAL_DATA
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
                vol.Required(
                    D_UPDATE_INTERVAL_ALARM, default=UPDATE_INTERVAL_ALARM
                ): vol.All(vol.Coerce(int), vol.Range(min=10)),
            }
        )

        return self.async_show_form(
            step_id=D_API_KEY,
            data_schema=data_schema,
            errors=self.errors,
        )

    def _show_reconfigure_form(self, current_interval_data, current_interval_alarm):
        """Display the reconfigure input form."""
        data_schema = vol.Schema(
            {
                vol.Required(
                    D_UPDATE_INTERVAL_DATA, default=current_interval_data
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
                vol.Required(
                    D_UPDATE_INTERVAL_ALARM, default=current_interval_alarm
                ): vol.All(vol.Coerce(int), vol.Range(min=10)),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=self.errors,
        )

    async def _process_hubs(self, clusters, user_input):
        """Process hub creation or identify existing hubs."""
        await self._create_hubs(clusters, user_input)

        if self.new_data and not self.existing_data:
            return self.async_abort(
                reason="new_data_only",
                description_placeholders={"new_data": ", ".join(self.new_data)},
            )

        if not self.new_data and self.existing_data:
            return self.async_abort(
                reason="existing_data_only",
                description_placeholders={
                    "existing_data": ", ".join(self.existing_data)
                },
            )

        if self.new_data and self.existing_data:
            return self.async_abort(
                reason="new_and_existing_data",
                description_placeholders={
                    "new_data": ", ".join(self.existing_data),
                    "existing_data": ", ".join(self.existing_data),
                },
            )

        return self.async_abort(reason="no_new_hubs_found")

    async def _create_hubs(self, clusters, user_input) -> None:
        """Create new hubs(clusters) if they do not already exist, or add devices(users) to existing hubs(clusters).

        Import:
        - clusters: dict - {cluster_id: cluster_data}
        - user_input: dict - {username, password, update_interval_data, update_interval_alarm}

        Export:
        - None, but writes to self.new_data and self.existing_data

        This method will check if there is an existing config_entry for the hub(cluster) the user entered. If so, a new device(user) will be
        created for the hub(cluster) by updating the existing entry. If not, a new cluster(entry) will be created.
        To be able to add multiple hubs at one, a task will be added per hub(cluster) to start async_create_entry.
        """

        processed_hubs = set()
        existing_entry = None
        new_devices = {}

        for cluster_id, cluster_data in clusters.items():
            cluster_name = cluster_data["cluster_name"]

            # checking for existing hub(cluster)
            for entry in self._async_current_entries():
                existing_cluster_id = entry.data.get(D_CLUSTER_ID)
                if existing_cluster_id == cluster_id:
                    existing_entry = entry
                    break

            if existing_entry:
                LOGGER.debug(
                    "Unit '%s' already exists, checking for missing users",
                    cluster_name,
                )

                # checking for existing device(user)
                existing_devices = dict(
                    existing_entry.data.get("user_cluster_relations", {})
                )

                for ucr_id, ucr_data in cluster_data.get(
                    "user_cluster_relations", {}
                ).items():
                    if ucr_id not in existing_devices:
                        new_devices[ucr_id] = ucr_data

                # create new devices(users) by updating config_entry
                if new_devices:
                    existing_devices.update(new_devices)
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={
                            **existing_entry.data,
                            "user_cluster_relations": existing_devices,
                        },
                    )
                    LOGGER.debug(
                        "Added new users to existing hub '%s': %s",
                        cluster_name,
                        list(new_devices.keys()),
                    )

                    # updating coordinator
                    async_dispatcher_send(
                        self.hass, f"{DOMAIN}_config_updated", existing_entry.entry_id
                    )

                    self.new_data.append(
                        f"\n{cluster_name} - {ucr_data.get(D_USERNAME)}"
                    )

                    continue

                LOGGER.debug("No new users found for hub '%s'", cluster_name)
                self.existing_data.append(
                    f"\n{cluster_name} - {ucr_data.get(D_USERNAME)}"
                )
                continue

            # creating hub(cluster)
            if cluster_id in processed_hubs:
                LOGGER.warning(
                    "Skipping duplicate hub creation attempt for '%s'", cluster_name
                )

                self.existing_data.append(f"\n{cluster_name}")
                continue

            new_hub = {
                D_CLUSTER_ID: cluster_id,
                D_UPDATE_INTERVAL_DATA: user_input[D_UPDATE_INTERVAL_DATA],
                D_UPDATE_INTERVAL_ALARM: user_input[D_UPDATE_INTERVAL_ALARM],
                "cluster_name": cluster_name,
                "user_cluster_relations": {
                    ucr_id: {
                        D_USERNAME: user_data.get("user_name"),
                        D_API_KEY: user_data.get(D_API_KEY),
                    }
                    for ucr_id, user_data in cluster_data.get(
                        "user_cluster_relations", {}
                    ).items()
                },
            }

            # mark hub(cluster) as processed
            processed_hubs.add(cluster_id)

            # create taks per found hub(cluster). each task will create an entry.
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": "import"}, data=new_hub
                )
            )

            for ucr_id, user_data in cluster_data.get(
                "user_cluster_relations", {}
            ).items():
                self.new_data.append(f"\n{cluster_name} - {user_data.get(D_USERNAME)}")

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle automatic creation of a hub configuration - usually from YAML.

        Import:
        - import_data: dict - {cluster_id, cluster_name, user_cluster_relations}

        Export:
        - ConfigFlowResult


        This method is used as a workaround to create multiple entries This is needed, if a user is member of multiple Divera-units.
        """

        LOGGER.info("Creating new hub '%s'", import_data["cluster_name"])
        return self.async_create_entry(
            title=import_data["cluster_name"], data=import_data
        )
