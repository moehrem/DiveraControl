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
    DC_MINOR_VERSION,
    UPDATE_INTERVAL_DATA,
    UPDATE_INTERVAL_ALARM,
    DC_VERSION,
    DC_PATCH_VERSION,
    D_API_KEY,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERNAME,
)

LOGGER = logging.getLogger(__name__)


class MyDiveraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for myDivera integration."""

    VERSION = DC_VERSION
    MINOR_VERSION = DC_MINOR_VERSION
    PATCH_VERSION = DC_PATCH_VERSION

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.session = None
        self.errors: dict[str, str] = {}
        self.cluster_created: list = []
        self.cluster_existing: list = []
        self.device_created: list = []
        self.device_existing: list = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step for user configuration."""
        self.session = async_get_clientsession(self.hass)

        if user_input is None:
            return self._show_user_form()

        self.errors, clusters, api_key = await dc.validate_login(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_api_key_form()

        return await self._process_hubs(clusters, api_key, user_input)

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the API key input step."""
        if user_input is None:
            return self._show_api_key_form()

        self.errors = {}
        self.errors, clusters, api_key = await dc.validate_api_key(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_user_form()

        return await self._process_hubs(clusters, api_key, user_input)

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
            new_api_key = user_input[D_API_KEY]
            new_interval_data = user_input[D_UPDATE_INTERVAL_DATA]
            new_interval_alarm = user_input[D_UPDATE_INTERVAL_ALARM]

            new_data = {
                **existing_entry.data,
                D_API_KEY: new_api_key,
                D_UPDATE_INTERVAL_DATA: new_interval_data,
                D_UPDATE_INTERVAL_ALARM: new_interval_alarm,
            }

            return self.async_update_reload_and_abort(
                existing_entry,
                data_updates=new_data,
            )

        current_interval_data = existing_entry.data.get(D_UPDATE_INTERVAL_DATA)
        current_interval_alarm = existing_entry.data.get(D_UPDATE_INTERVAL_ALARM)
        api_key = existing_entry.data.get(D_API_KEY)

        return self._show_reconfigure_form(
            current_interval_data, current_interval_alarm, api_key
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

    def _show_reconfigure_form(
        self, current_interval_data, current_interval_alarm, api_key
    ):
        """Display the reconfigure input form."""
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_API_KEY, default=api_key): cv.string,
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

    async def _process_hubs(self, clusters, api_key, user_input):
        """Process hub creation or identify existing hubs."""
        await self._create_hubs(clusters, api_key, user_input)

        if self.cluster_created:
            return self.async_abort(
                reason="cluster_created",
                description_placeholders={"names": ", ".join(self.cluster_created)},
            )

        if self.device_created:
            return self.async_abort(
                reason="device_created",
                description_placeholders={"names": ", ".join(self.device_created)},
            )

        if self.cluster_existing:
            return self.async_abort(
                reason="cluster_existing",
                description_placeholders={"names": ", ".join(self.cluster_existing)},
            )

        if self.device_existing:
            return self.async_abort(
                reason="device_existing",
                description_placeholders={"names": ", ".join(self.device_existing)},
            )

        return self.async_abort(reason="no_new_hubs_found")

    async def _create_hubs(self, clusters, api_key, user_input):
        """Create new hubs if they do not already exist, or add user_cluster_relations to existing hubs."""
        processed_hubs = set()  # Verhindert doppelte Erstellung
        existing_entry = None
        new_devices = {}

        for cluster_id, cluster_data in clusters.items():
            cluster_name = cluster_data["cluster_name"]

            # Prüfen, ob der Hub bereits existiert
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

                # check if device(user) exists
                existing_devices = existing_entry.data.get("user_cluster_relations", {})

                for ucr_id, ucr_data in cluster_data.get(
                    "user_cluster_relations", {}
                ).items():
                    if ucr_id not in existing_devices:
                        new_devices[ucr_id] = ucr_data

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

                    # **Sende das Event NACH der Datenaktualisierung**
                    async_dispatcher_send(
                        self.hass, f"{DOMAIN}_config_updated", existing_entry.entry_id
                    )

                    self.device_created.append(f"\n{ucr_id}")
                    continue

                LOGGER.debug("No new users found for hub '%s'", cluster_name)
                self.device_existing.append(f"\n{cluster_name}")
                continue

            # Falls der Hub noch nicht existiert und noch nicht verarbeitet wurde
            if cluster_id in processed_hubs:
                LOGGER.warning(
                    "Skipping duplicate hub creation attempt for '%s'", cluster_name
                )
                continue

            # Erstelle einen neuen Hub für die Cluster-ID
            new_hub = {
                D_CLUSTER_ID: cluster_id,
                # D_API_KEY: api_key,
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

            # Markiere diesen Hub als verarbeitet
            processed_hubs.add(cluster_id)

            # Starte den Konfigurationsprozess für den neuen Hub
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": "import"}, data=new_hub
                )
            )
            self.cluster_created.append(f"\n{cluster_name}")

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle automatic creation of a hub configuration from YAML."""
        existing_entry = next(
            (
                entry
                for entry in self._async_current_entries()
                if entry.data.get(D_CLUSTER_ID) == import_data[D_CLUSTER_ID]
            ),
            None,
        )

        if existing_entry:
            LOGGER.info(
                "Hub '%s' already exists, checking for missing users",
                import_data["cluster_name"],
            )

            existing_cluster_id = existing_entry.data.get(D_CLUSTER_ID)
            hass_data = self.hass.data.get(DOMAIN, {})
            coordinator = hass_data.get(existing_cluster_id, {}).get("coordinator")

            if not coordinator:
                LOGGER.warning(
                    "No coordinator found for hub '%s'. Users may not be updated.",
                    import_data["cluster_name"],
                )
                return self.async_abort(reason="hubs_existing")

            existing_devices = existing_entry.data.get("user_cluster_relations", {})

            # Nur fehlende Geräte hinzufügen
            new_devices = {}

            for ucr_id, user_name in import_data.get(
                "user_cluster_relations", {}
            ).items():
                if ucr_id not in existing_devices:
                    new_devices[ucr_id] = {D_UCR_ID: ucr_id}

            if new_devices:
                existing_devices.update(new_devices)
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    data={
                        **existing_entry.data,
                        "user_cluster_relations": existing_devices,
                    },
                )

                LOGGER.info(
                    "Added new users to existing hub '%s': %s",
                    import_data["cluster_name"],
                    list(new_devices.keys()),
                )

                # **Coordinator über die Änderung informieren**
                async_dispatcher_send(
                    self.hass, f"{DOMAIN}_config_updated", existing_entry.entry_id
                )

                return self.async_abort(reason="hubs_existing")

            LOGGER.info(
                "No new users found for existing hub '%s'",
                import_data["cluster_name"],
            )

            return self.async_abort(reason="hubs_existing")

        LOGGER.info("Creating new hub '%s'", import_data["cluster_name"])
        return self.async_create_entry(
            title=import_data["cluster_name"], data=import_data
        )
