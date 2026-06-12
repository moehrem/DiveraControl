"""Config flow for myDivera integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback

from .const import (
    BASE_API_URL,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_RELATIONS_KEY,
    DOMAIN,
)
from .divera_api import DiveraAPIClient
from .options_flow import DiveraControlOptionsFlow
from .schemas import (
    get_api_key_form_schema,
    get_login_form_schema,
    get_multi_cluster_form_schema,
)

_LOGGER = logging.getLogger(__name__)
STEP_USER = "user"
STEP_LOGIN = "login"
STEP_API_KEY = "accesskey"
STEP_MULTI_CLUSTER = "multi_cluster"


class DiveraControlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for DiveraControl integration."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.final_entry: dict[str, Any] | None = None
        self.possible_entries: dict[str, dict[str, Any]] = {}
        self.errors: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DiveraControlOptionsFlow:
        """Create the options flow for this config entry."""
        return DiveraControlOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle Home Assistant's initial user step by forwarding to login."""
        return await self.async_step_login(user_input)

    async def async_step_login(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle login with user credentials."""
        if user_input is None:
            return self._show_login_form()
        return await self._validate_user_data(user_input)

    async def async_step_api_key(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the API key input step."""
        if user_input is None:
            return self._show_api_key_form()
        return await self._validate_user_data(user_input)

    async def async_step_multi_cluster(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the multi-cluster input step."""
        if user_input is None:
            return self._show_multi_cluster_form()

        _selected_cluster = user_input["clusters"]
        _selected_cluster_id = self._get_cluster_id_by_name(_selected_cluster)

        if _selected_cluster_id is None:
            return self.async_abort(reason="unknown_step")

        self.final_entry = self.possible_entries.get(_selected_cluster_id)
        return await self._upsert_cluster()

    def _show_form(
        self,
        step_id: str,
        schema: vol.Schema,
    ) -> ConfigFlowResult:
        """Generic method to show a form with errors."""
        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=self.errors,
        )

    def _show_login_form(
        self, defaults: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the login form with saved defaults."""
        if defaults is None:
            defaults = {}
        return self._show_form(
            STEP_LOGIN,
            get_login_form_schema(defaults),
        )

    def _show_api_key_form(
        self, defaults: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the API key form with saved defaults."""
        if defaults is None:
            defaults = {}
        return self._show_form(
            STEP_API_KEY,
            get_api_key_form_schema(defaults),
        )

    def _show_multi_cluster_form(self) -> ConfigFlowResult:
        """Show cluster picker when multiple clusters are available."""
        cluster_names = [
            entry_data[D_CLUSTER_NAME] for entry_data in self.possible_entries.values()
        ]
        return self._show_form(
            STEP_MULTI_CLUSTER,
            get_multi_cluster_form_schema(cluster_names),
        )

    def _get_cluster_id_by_name(self, cluster_name: str) -> str | None:
        """Resolve a selected cluster name back to its cluster id."""
        return next(
            (
                cluster_id
                for cluster_id, entry_data in self.possible_entries.items()
                if entry_data[D_CLUSTER_NAME] == cluster_name
            ),
            None,
        )

    async def _request_possible_entries(self, user_input: dict[str, Any]) -> None:
        """Call API for access validation and candidate clusters."""
        base_api_url = user_input.get(D_BASE_API_URL, BASE_API_URL)
        config_flow_api = DiveraAPIClient(self.hass, base_api_url)
        self.errors, self.possible_entries = await config_flow_api.request_access(
            user_input
        )

    def _resolve_cluster_selection(self) -> ConfigFlowResult | None:
        """Resolve cluster selection or show picker when needed."""
        if len(self.possible_entries) > 1:
            return self._show_multi_cluster_form()

        if self.possible_entries:
            selected_cluster = next(iter(self.possible_entries))
            self.final_entry = self.possible_entries.get(selected_cluster)

        return None

    async def _validate_user_data(
        self,
        user_input: dict[str, Any],
    ) -> ConfigFlowResult:
        """Validate user input and decide next steps."""
        self.errors.clear()
        await self._request_possible_entries(user_input)

        if self.errors:
            return await self._error_handling()

        self._handle_duplicates()

        cluster_step = self._resolve_cluster_selection()
        if cluster_step is not None:
            return cluster_step

        return await self._upsert_cluster()

    async def _error_handling(self) -> ConfigFlowResult:
        """Handle errors by showing the current form again with error messages."""
        error_number = self.errors.get("number", 0)
        if error_number != 0:
            return self._show_api_key_form()

        cur_step_id = self.cur_step.get("step_id", STEP_USER)

        # Mapping: step_id -> form_handler
        form_handlers = {
            STEP_USER: self._show_login_form,
            STEP_LOGIN: self._show_login_form,
            STEP_API_KEY: self._show_api_key_form,
            STEP_MULTI_CLUSTER: self._show_multi_cluster_form,
        }

        handler = form_handlers.get(cur_step_id, self._show_login_form)
        return handler()

    def _get_existing_ucr_ids(self, entry: ConfigEntry) -> set[str]:
        """Extract all UCR IDs from an existing config entry."""
        existing_relations = entry.data.get(D_RELATIONS_KEY, {})
        if not isinstance(existing_relations, dict):
            return set()

        return {str(ucr_id) for ucr_id in existing_relations.keys()}

    def _find_duplicate_ucr_ids(
        self, new_relations: dict[str, Any], existing_ucr_ids: set[str]
    ) -> set[str]:
        """Find duplicate UCR IDs in new_relations that already exist."""
        return {
            str(ucr_id)
            for ucr_id in new_relations.keys()
            if str(ucr_id) in existing_ucr_ids
        }

    def _handle_duplicates(self) -> None:
        """Handle duplicate clusters and users."""
        clusters_to_remove: list[str] = []

        for cluster_id, cluster_data in self.possible_entries.items():
            new_relations = cluster_data.get(D_RELATIONS_KEY, {})

            # Find existing entry for this cluster
            existing_config_entry = self._find_existing_cluster_entry(cluster_id)

            # Cluster is not configured yet: keep all new users
            if existing_config_entry is None:
                continue

            # Get existing UCR IDs
            existing_ucr_ids = self._get_existing_ucr_ids(existing_config_entry)
            if not existing_ucr_ids:
                continue

            # Find and remove duplicates
            duplicate_ucr_ids = self._find_duplicate_ucr_ids(
                new_relations, existing_ucr_ids
            )

            if duplicate_ucr_ids:
                _LOGGER.debug(
                    "Skipping duplicate users for cluster '%s': %s",
                    cluster_id,
                    ", ".join(sorted(duplicate_ucr_ids)),
                )

            for ucr_id in duplicate_ucr_ids:
                new_relations.pop(ucr_id, None)

            # Remove empty clusters
            if not new_relations:
                clusters_to_remove.append(cluster_id)

        # Clean up empty clusters
        for cluster_id in clusters_to_remove:
            self.possible_entries.pop(cluster_id, None)

    def _find_existing_cluster_entry(self, cluster_id: str) -> ConfigEntry | None:
        """Return existing config entry for a cluster id, if configured."""
        return next(
            (
                entry
                for entry in self._async_current_entries()
                if str(entry.data.get(D_CLUSTER_ID, "")) == str(cluster_id)
            ),
            None,
        )

    async def _upsert_cluster(self) -> ConfigFlowResult:
        """Create a new cluster entry or merge missing user relations."""
        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        selected_cluster_id = str(self.final_entry.get(D_CLUSTER_ID, ""))
        if not selected_cluster_id:
            return self.async_abort(reason="no_new_hubs_found")

        existing_config_entry = self._find_existing_cluster_entry(selected_cluster_id)
        if existing_config_entry is None:
            return await self._create_cluster()

        new_relations = self.final_entry.get(D_RELATIONS_KEY, {})
        if not new_relations:
            return self.async_abort(reason="already_configured")

        existing_relations = existing_config_entry.data.get(D_RELATIONS_KEY, {})
        if not isinstance(existing_relations, dict):
            existing_relations = {}

        merged_relations = {
            str(ucr_id): relation_data
            for ucr_id, relation_data in existing_relations.items()
        }

        added_relations = 0
        for ucr_id, relation_data in new_relations.items():
            if ucr_id in merged_relations:
                continue

            merged_relations[ucr_id] = relation_data
            added_relations += 1

        if added_relations == 0:
            return self.async_abort(reason="already_configured")

        self.hass.config_entries.async_update_entry(
            existing_config_entry,
            data={
                **existing_config_entry.data,
                D_RELATIONS_KEY: merged_relations,
            },
        )

        _LOGGER.debug(
            "Adding %s user relation(s) to existing cluster '%s'",
            added_relations,
            selected_cluster_id,
        )

        self.hass.config_entries.async_schedule_reload(existing_config_entry.entry_id)
        return self.async_abort(reason="merge_successful")

    async def _create_cluster(self) -> ConfigFlowResult:
        """Process device creation."""
        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        selected_cluster_id = self.final_entry.get(D_CLUSTER_ID)
        await self.async_set_unique_id(selected_cluster_id)

        return self.async_create_entry(
            title=self.final_entry[D_CLUSTER_NAME],
            data=self.final_entry,
        )
