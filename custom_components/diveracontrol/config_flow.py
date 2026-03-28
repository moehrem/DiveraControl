"""Config flow for myDivera integration."""

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_USERNAME
from homeassistant.core import callback

from .const import (
    BASE_API_URL,
    D_API_KEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERNAME,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
    VERSION,
)
from .divera_api import DiveraConfigFlowAPI
from .schemas import (
    get_api_key_form_schema,
    get_login_form_schema,
    get_multi_cluster_form_schema,
    get_reconfigure_ucr_form_schema,
)

LOGGER = logging.getLogger(__name__)
SUBENTRY_TYPE_USER_RELATION = "user_relation"
STEP_USER = "user"
STEP_LOGIN = "login"
STEP_MULTI_CLUSTER = "multi_cluster"


class DiveraControlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for DiveraControl integration."""

    VERSION = VERSION
    MINOR_VERSION = MINOR_VERSION
    PATCH_VERSION = PATCH_VERSION

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported subentry types for this integration."""

        return {
            SUBENTRY_TYPE_USER_RELATION: DiveraUserRelationSubentryFlow,
        }

    def __init__(self) -> None:
        """Initialize the config flow.

        Returns:
            None

        """
        self.final_entry: dict[str, Any] | None = None
        self.possible_entries: dict[str, dict[str, Any]] = {}
        self.errors: dict[str, str] = {}
        self._saved_login: dict[str, Any] = {}
        self._saved_api_key: dict[str, Any] = {}

    @staticmethod
    def _subentry_title(relation_data: dict[str, Any], ucr_id: str) -> str:
        """Build a stable title for user relation subentries."""

        return str(relation_data.get("username") or ucr_id)

    @classmethod
    def _relation_subentries(
        cls, relations: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert relation mapping into config subentry payloads."""

        subentries: list[dict[str, Any]] = []
        for raw_ucr_id, relation_data in relations.items():
            ucr_id = str(raw_ucr_id)
            relation_dict = dict(relation_data)
            relation_dict[D_UCR_ID] = relation_dict.get(D_UCR_ID, ucr_id)

            subentries.append(
                {
                    "data": relation_dict,
                    "subentry_type": SUBENTRY_TYPE_USER_RELATION,
                    "title": cls._subentry_title(relation_dict, ucr_id),
                    "unique_id": ucr_id,
                }
            )

        return subentries

    @staticmethod
    def _normalized_relation_data(
        ucr_id: str,
        relation_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize relation data, ensuring D_UCR_ID is set."""

        normalized = dict(relation_data)
        normalized[D_UCR_ID] = normalized.get(D_UCR_ID, ucr_id)
        return normalized

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
        """Handle the API key input step.

        Will be called only if the given credentials reveal a user-class, that's not allowed to login.

        Args:
            user_input: The user input data of step "api_key".

        Returns:
            ConfigFlowResult: The result of the config flow step "api_key".

        """

        if user_input is None:
            return self._show_api_key_form()

        return await self._validate_user_data(user_input)

    async def async_step_multi_cluster(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the multi-cluster input step.

        Args:
            user_input: The user input data of step "multi_cluster".

        Returns:
            ConfigFlowResult: The result of the config flow step "multi_cluster".

        """

        if user_input is None:
            return self._show_multi_cluster_form()

        _selected_cluster = user_input["clusters"]
        _selected_cluster_id = self._get_cluster_id_by_name(_selected_cluster)

        if _selected_cluster_id is None:
            return self.async_abort(reason="unknown_step")

        self.final_entry = self.possible_entries.get(_selected_cluster_id)

        return await self._upsert_cluster()

    def _show_login_form(self) -> ConfigFlowResult:
        """Show the login form with saved defaults."""

        defaults = getattr(self, "_saved_login", {})
        return self.async_show_form(
            step_id=STEP_LOGIN,
            data_schema=get_login_form_schema(defaults),
            errors=self.errors,
        )

    def _show_api_key_form(self) -> ConfigFlowResult:
        """Show the API key form with saved defaults."""

        defaults = getattr(self, "_saved_api_key", {})
        return self.async_show_form(
            step_id=D_API_KEY,
            data_schema=get_api_key_form_schema(defaults),
            errors=self.errors,
        )

    def _show_multi_cluster_form(self) -> ConfigFlowResult:
        """Show cluster picker when multiple clusters are available."""

        cluster_names = [
            entry_data[D_CLUSTER_NAME] for entry_data in self.possible_entries.values()
        ]
        return self.async_show_form(
            step_id=STEP_MULTI_CLUSTER,
            data_schema=get_multi_cluster_form_schema(cluster_names),
            errors=self.errors,
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

    def _persist_input(self, user_input: dict[str, Any]) -> None:
        """Persist non-sensitive user input for form defaults.

        Args:
            user_input: The user input data of the current step.

        """

        cur_step_id = self.cur_step.get("step_id", STEP_USER)
        if cur_step_id in (STEP_USER, STEP_LOGIN):
            # do not persist password
            self._saved_login = {
                CONF_USERNAME: user_input.get(CONF_USERNAME, ""),
                D_UPDATE_INTERVAL_DATA: user_input.get(
                    D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
                ),
                D_UPDATE_INTERVAL_ALARM: user_input.get(
                    D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                ),
                D_BASE_API_URL: user_input.get(D_BASE_API_URL, BASE_API_URL),
            }
        elif cur_step_id == D_API_KEY:
            self._saved_api_key = {
                D_API_KEY: user_input.get(D_API_KEY, ""),
                D_UPDATE_INTERVAL_DATA: user_input.get(
                    D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
                ),
                D_UPDATE_INTERVAL_ALARM: user_input.get(
                    D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                ),
                D_BASE_API_URL: user_input.get(D_BASE_API_URL, BASE_API_URL),
            }

    async def _request_possible_entries(self, user_input: dict[str, Any]) -> None:
        """Call API for access validation and candidate clusters."""

        base_api_url = user_input.get(D_BASE_API_URL, BASE_API_URL)
        config_flow_api = DiveraConfigFlowAPI(self.hass, base_api_url)
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
        """Validate user input and decide next steps.

        Called from either the "user" or "login" step, depending on the current step of the flow.
        Persist user input for form defaults. Validate credentials and get possible cluster entries.
        If errors, show the current form again. If multiple clusters found, ask user to select a cluster. Else, proceed with the single found cluster.

        Args:
            user_input (dict[str, Any]): The user input data of the current step.

        Returns:
            ConfigFlowResult: The result of the config flow step.

        """

        self.errors.clear()
        await self._request_possible_entries(user_input)

        # error handling: show the current step again so the user can fix input
        if self.errors:
            return await self._error_handling(user_input)

        # check duplicate entries and users
        self._handle_duplicates()

        cluster_step = self._resolve_cluster_selection()
        if cluster_step is not None:
            return cluster_step

        return await self._upsert_cluster()

    async def _error_handling(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle errors by showing the current form again with error messages.

        Args:
            user_input (dict[str, Any]): The user input data of the current step.

        Returns:
            ConfigFlowResult: The result of showing the form again with errors.

        """

        self._persist_input(user_input)

        cur_step_id = self.cur_step.get("step_id", STEP_USER)
        error_number = self.errors.get("number", 0)

        # check for specific error numbers first: show api form then
        if error_number != 0:
            return self._show_api_key_form()

        # for other errors, show the form of the current step again
        if cur_step_id in (STEP_USER, STEP_LOGIN):
            return self._show_login_form()

        if cur_step_id == D_API_KEY:
            return self._show_api_key_form()

        return self._show_login_form()

    def _handle_duplicates(self) -> None:
        """Handle duplicate clusters and users.

        Check for duplicate clusters/config entries. If so, check the clusters for duplicate users.
        Delete duplicate users. And delete empty clusters without users.

        """

        existing_entries = list(self._async_current_entries())
        clusters_to_remove: list[str] = []

        for cluster_id, cluster_data in self.possible_entries.items():
            new_relations = cluster_data.get(D_RELATIONS_KEY, {})

            if not isinstance(new_relations, dict):
                clusters_to_remove.append(cluster_id)
                continue

            existing_entry = next(
                (
                    entry
                    for entry in existing_entries
                    if str(entry.data.get(D_CLUSTER_ID, "")) == cluster_id
                ),
                None,
            )

            # Cluster is not configured yet: keep all new users.
            if existing_entry is None:
                continue

            existing_ucr_ids = {
                str(subentry.unique_id or subentry.data.get(D_UCR_ID, ""))
                for subentry in existing_entry.subentries.values()
                if str(subentry.unique_id or subentry.data.get(D_UCR_ID, ""))
            }

            if not existing_ucr_ids:
                continue

            duplicate_ucr_ids = {
                str(ucr_id)
                for ucr_id, relation_data in new_relations.items()
                if str(ucr_id) in existing_ucr_ids
                or (
                    isinstance(relation_data, dict)
                    and str(relation_data.get(D_UCR_ID, "")) in existing_ucr_ids
                )
            }

            if duplicate_ucr_ids:
                LOGGER.debug(
                    "Skipping duplicate users for cluster '%s': %s",
                    cluster_id,
                    ", ".join(sorted(duplicate_ucr_ids)),
                )

            for ucr_id in duplicate_ucr_ids:
                new_relations.pop(ucr_id, None)

            # Remove empty clusters that no longer contain new users.
            if not new_relations:
                clusters_to_remove.append(cluster_id)

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
        """Create a new cluster entry or add missing user subentries."""

        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        selected_cluster_id = str(self.final_entry.get(D_CLUSTER_ID, ""))
        if not selected_cluster_id:
            return self.async_abort(reason="no_new_hubs_found")

        existing_entry = self._find_existing_cluster_entry(selected_cluster_id)
        if existing_entry is None:
            return await self._create_cluster()

        new_relations = self.final_entry.get(D_RELATIONS_KEY, {})
        if not isinstance(new_relations, dict) or not new_relations:
            return self.async_abort(reason="already_configured")

        existing_ucr_ids = {
            str(subentry.unique_id or subentry.data.get(D_UCR_ID, ""))
            for subentry in existing_entry.subentries.values()
            if str(subentry.unique_id or subentry.data.get(D_UCR_ID, ""))
        }

        added_subentries = 0
        for raw_ucr_id, relation_data in new_relations.items():
            ucr_id = str(raw_ucr_id)
            if ucr_id in existing_ucr_ids:
                continue

            relation_dict = self._normalized_relation_data(ucr_id, relation_data)

            self.hass.config_entries.async_add_subentry(
                existing_entry,
                ConfigSubentry(
                    data=MappingProxyType(relation_dict),
                    subentry_type=SUBENTRY_TYPE_USER_RELATION,
                    title=self._subentry_title(relation_dict, ucr_id),
                    unique_id=ucr_id,
                ),
            )
            added_subentries += 1

        if added_subentries == 0:
            return self.async_abort(reason="already_configured")

        LOGGER.debug(
            "Adding %s user relation(s) to existing cluster '%s'",
            added_subentries,
            selected_cluster_id,
        )

        self.hass.config_entries.async_schedule_reload(existing_entry.entry_id)
        return self.async_abort(reason="merge_successful")

    async def _create_cluster(self) -> ConfigFlowResult:
        """Process device creation.

        Returns:
            ConfigFlowResult: The result of the config flow step "configure".

        """

        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        selected_cluster_id = self.final_entry.get(D_CLUSTER_ID)

        # just for HA best practice and logging
        # duplicates are handled earlier already and do not reach this point
        await self.async_set_unique_id(selected_cluster_id)

        relations = self.final_entry.get(D_RELATIONS_KEY, {})
        if not isinstance(relations, dict):
            relations = {}

        entry_data = {
            key: value
            for key, value in self.final_entry.items()
            if key != D_RELATIONS_KEY
        }

        return self.async_create_entry(
            title=self.final_entry[D_CLUSTER_NAME],
            data=entry_data,
            subentries=self._relation_subentries(relations),
        )


class DiveraUserRelationSubentryFlow(ConfigSubentryFlow):
    """Handle user relation subentry reconfiguration."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle the initial step for user relation reconfiguration.

        This is a placeholder, as HA implements the buttons to add subentries once the integration integrates "ConfigSubentryFlow".
        This step just gives the message that adding new subentries is not supported directly, instead the user should add a new hub.

        Within the main config_flow all steps for new hubs/units and/or users/ucrs are implemented.

        """

        return self.async_abort(reason="add_user_via_cluster")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure an existing user relation subentry."""

        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            title = str(
                user_input.get(D_USERNAME)
                or subentry.data.get(D_USERNAME)
                or subentry.unique_id
                or subentry.subentry_id
            )

            return self.async_update_reload_and_abort(
                entry=entry,
                subentry=subentry,
                title=title,
                data_updates={
                    D_USERNAME: user_input.get(D_USERNAME),
                    D_API_KEY: user_input.get(D_API_KEY),
                    D_BASE_API_URL: user_input.get(D_BASE_API_URL),
                    D_UPDATE_INTERVAL_DATA: user_input.get(D_UPDATE_INTERVAL_DATA),
                    D_UPDATE_INTERVAL_ALARM: user_input.get(D_UPDATE_INTERVAL_ALARM),
                },
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_reconfigure_ucr_form_schema(dict(subentry.data)),
        )
