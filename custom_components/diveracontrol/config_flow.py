"""Config flow for myDivera integration."""

from collections.abc import Callable
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    BASE_API_URL,
    D_API_KEY,
    D_CLUSTER_ID,
    D_BASE_API_URL,
    D_CLUSTER_NAME,
    D_INTEGRATION_VERSION,
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USE_WEBHOOKS,
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
    get_entry_form_schema,
    get_login_form_schema,
    get_multi_cluster_form_schema,
    get_reconfigure_form_schema,
)
from .webhook_handler import WebhookHandler

LOGGER = logging.getLogger(__name__)


class DiveraControlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for DiveraControl integration."""

    VERSION = VERSION
    MINOR_VERSION = MINOR_VERSION
    PATCH_VERSION = PATCH_VERSION

    def __init__(self) -> None:
        """Initialize the config flow.

        Returns:
            None

        """

        self.session: aiohttp.ClientSession | None = None
        self.reconf_config_entry: ConfigEntry | None = None
        self.final_entry: dict[str, Any] | None = None
        self.possible_entries: dict[str, dict[str, Any]] = {}
        self.errors: dict[str, str] = {}
        self.reconfigure = False
        self.webhook_handler: WebhookHandler | None = None
        self._saved_login: dict[str, Any] = {}
        self._saved_api_key: dict[str, Any] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step for user configuration.

        Args:
            user_input: The user input data of step "user".

        Returns:
            ConfigFlowResult: The result of the config flow step "user".

        """

        self.session = async_get_clientsession(self.hass)

        # Show a small form at the entry instead of a menu. Using a form
        # allows us to present errors on the same screen when validation
        # fails and to keep a consistent UI.
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=get_entry_form_schema(),
                errors=self.errors,
            )

        # choose next step depending on user selection
        method = user_input.get("method")
        if method == "login":
            return await self.async_step_login()
        if method == "api_key":
            return await self.async_step_api_key()

        return self.async_show_form(
            step_id="user",
            data_schema=get_entry_form_schema(),
            errors=self.errors,
        )

    async def async_step_login(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle user login step.

        Args:
            user_input: The user input data of step "login".

        Returns:
            ConfigFlowResult: The result of the config flow step "login".

        """

        if user_input is None:
            defaults = getattr(self, "_saved_login", {})
            return self.async_show_form(
                step_id="login",
                data_schema=get_login_form_schema(defaults),
                errors=self.errors,
            )

        return await self._validate_and_proceed(
            DiveraConfigFlowAPI.validate_login, user_input
        )

    async def async_step_api_key(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the API key input step.

        Args:
            user_input: The user input data of step "api_key".

        Returns:
            ConfigFlowResult: The result of the config flow step "api_key".

        """

        if user_input is None:
            defaults = getattr(self, "_saved_api_key", {})
            return self.async_show_form(
                step_id=D_API_KEY,
                data_schema=get_api_key_form_schema(defaults),
                errors=self.errors,
            )

        return await self._validate_and_proceed(
            DiveraConfigFlowAPI.validate_api_key, user_input
        )

    async def async_step_webhook_info(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show webhook URL information before finishing setup."""

        if user_input is None:
            webhook_url = ""
            if self.webhook_handler is not None:
                webhook_url = self.webhook_handler.webhook_url
            return self.async_show_form(
                step_id="webhook_info",
                data_schema=vol.Schema({}),
                description_placeholders={"webhook_url": webhook_url},
                errors=self.errors,
            )

        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        if self.reconfigure:
            if self.reconf_config_entry is None:
                return self.async_abort(reason="reconfigure_failed")
            return self.async_update_reload_and_abort(
                self.reconf_config_entry,
                data_updates=self.final_entry,
            )

        return self.async_create_entry(
            title=self.final_entry[D_CLUSTER_NAME],
            data=self.final_entry,
        )

    async def async_step_webhook_error(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show webhook URL error before finishing setup."""

        if user_input is None:
            return self.async_show_form(
                step_id="webhook_error",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "remote_docs_url": "https://www.home-assistant.io/docs/configuration/remote/"
                },
                errors=self.errors,
            )

        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        if self.reconfigure:
            if self.reconf_config_entry is None:
                return self.async_abort(reason="reconfigure_failed")
            return self.async_update_reload_and_abort(
                self.reconf_config_entry,
                data_updates=self.final_entry,
            )

        return self.async_create_entry(
            title=self.final_entry[D_CLUSTER_NAME],
            data=self.final_entry,
        )

    async def async_step_multi_cluster(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the multi-cluster input step.

        Args:
            user_input: The user input data of step "multi_cluster".

        Returns:
            ConfigFLowResult: The result of the config flow step "multi_cluster".

        """

        if user_input is None:
            cluster_names = [
                entry_data[D_CLUSTER_NAME]
                for entry_data in self.possible_entries.values()
            ]
            return self.async_show_form(
                step_id="multi_cluster",
                data_schema=get_multi_cluster_form_schema(cluster_names),
                errors=self.errors,
            )

        _selected_cluster = user_input["clusters"]
        _selected_cluster_id = next(
            (
                cluster_id
                for cluster_id, entry_data in self.possible_entries.items()
                if entry_data[D_CLUSTER_NAME] == _selected_cluster
            ),
            None,
        )

        if _selected_cluster_id is None:
            return self.async_abort(reason="unknown_step")

        self.final_entry = self.possible_entries.get(_selected_cluster_id)

        return await self._upsert_cluster()

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing hub.

        Args:
            user_input: The user input data of step "reconfigure".

        Returns:
            ConfigFlowResult: The result of the config flow step "reconfigure".

        """

        entry_id: str | None = self.context.get("entry_id")
        if entry_id is None:
            return self.async_abort(reason="reconfigure_failed")

        self.reconf_config_entry = self.hass.config_entries.async_get_entry(entry_id)
        if self.reconf_config_entry is None:
            return self.async_abort(reason="reconfigure_failed")

        self.reconfigure = True

        current_interval_data: int = self.reconf_config_entry.data.get(
            D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
        )
        current_interval_alarm: int = self.reconf_config_entry.data.get(
            D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
        )
        current_api_key: str = self.reconf_config_entry.data.get(D_API_KEY, "")
        current_base_api_url: str = self.reconf_config_entry.data.get(
            D_BASE_API_URL, BASE_API_URL
        )
        current_use_webhooks: bool = self.reconf_config_entry.data.get(
            D_USE_WEBHOOKS, False
        )

        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=get_reconfigure_form_schema(
                    current_interval_data,
                    current_interval_alarm,
                    current_api_key,
                    current_base_api_url,
                    current_use_webhooks,
                ),
                errors=self.errors,
            )

        new_api_key = user_input[D_API_KEY]
        new_interval_data = user_input[D_UPDATE_INTERVAL_DATA]
        new_interval_alarm = user_input[D_UPDATE_INTERVAL_ALARM]
        new_base_api_url = user_input[D_BASE_API_URL]
        new_use_webhooks = user_input[D_USE_WEBHOOKS]

        new_data = {
            **self.reconf_config_entry.data,
            D_API_KEY: new_api_key,
            D_UPDATE_INTERVAL_DATA: new_interval_data,
            D_UPDATE_INTERVAL_ALARM: new_interval_alarm,
            D_BASE_API_URL: new_base_api_url,
            D_USE_WEBHOOKS: new_use_webhooks,
        }

        self.final_entry = new_data

        return await self._reconfigure_cluster()

    async def _persist_input(self, user_input: dict[str, Any]) -> None:
        """Persist non-sensitive user input for form defaults.

        Args:
            user_input: The user input data of the current step.

        """

        cur_step_id = self.cur_step.get("step_id") if self.cur_step else None
        if cur_step_id == "login":
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
                D_USE_WEBHOOKS: user_input.get(D_USE_WEBHOOKS, False),
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

    async def _validate_and_proceed(
        self,
        validation_method: Callable[[dict[str, str], Any, dict[str, Any], str], Any],
        user_input: dict[str, Any],
    ) -> ConfigFlowResult:
        """Validate user input and decide next steps.

        Args:
            validation_method (callable): The validation method to be used, might be `DiveraConfigFlowAPI.validate_login` or `DiveraConfigFlowAPI.validate_api_key`.
            user_input (dict[str, Any]): The user input data of step "reconfigure".

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        self.errors.clear()

        await self._persist_input(user_input)

        # set base values
        _update_interval_data = user_input.get(
            D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
        )
        _update_interval_alarm = user_input.get(
            D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
        )
        _base_api_url = user_input.get(D_BASE_API_URL, BASE_API_URL)
        _use_webhooks = user_input.get(D_USE_WEBHOOKS, False)

        # validate api_key or user login
        # get possible entries
        self.errors, self.possible_entries = await validation_method(
            self.session, user_input, _base_api_url
        )

        # error handling: show the current step again so the user can fix input
        if self.errors:
            cur_step_id = self.cur_step.get("step_id") if self.cur_step else None
            if cur_step_id == "login":
                defaults = getattr(self, "_saved_login", {})
                return self.async_show_form(
                    step_id="login",
                    data_schema=get_login_form_schema(defaults),
                    errors=self.errors,
                )
            if cur_step_id == D_API_KEY:
                defaults = getattr(self, "_saved_api_key", {})
                return self.async_show_form(
                    step_id=D_API_KEY,
                    data_schema=get_api_key_form_schema(defaults),
                    errors=self.errors,
                )
            return self.async_show_form(
                step_id="user",
                data_schema=get_entry_form_schema(),
                errors=self.errors,
            )

        # set missing parameters
        for cluster_data in self.possible_entries.values():
            cluster_data[D_UPDATE_INTERVAL_ALARM] = _update_interval_alarm
            cluster_data[D_UPDATE_INTERVAL_DATA] = _update_interval_data
            cluster_data[D_USE_WEBHOOKS] = _use_webhooks

        # check duplicate entries and users
        self._handle_duplicates()

        # if more units available, ask user to choose a unit
        if len(self.possible_entries) > 1:
            cluster_names = [
                entry_data[D_CLUSTER_NAME]
                for entry_data in self.possible_entries.values()
            ]
            return self.async_show_form(
                step_id="multi_cluster",
                data_schema=get_multi_cluster_form_schema(cluster_names),
                errors=self.errors,
            )

        # else set single entry as final entry for creation and proceed
        if self.possible_entries:
            _selected_cluster = next(iter(self.possible_entries))
            self.final_entry = self.possible_entries.get(_selected_cluster)

        return await self._upsert_cluster()

    def _handle_duplicates(self) -> None:
        """Handle duplicate clusters and users.

        Check for duplicate clusters/config entries. If so, check the clusters for duplicate users.
        Delete duplicate users. And delete empty clusters without users.

        Args:
            None

        Returns:
            None

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

            existing_relations = existing_entry.data.get(D_RELATIONS_KEY, {})
            existing_ucr_ids: set[str] = set()

            # New format: users are stored in user_cluster_relations.
            if isinstance(existing_relations, dict):
                for ucr_key, relation_data in existing_relations.items():
                    existing_ucr_ids.add(str(ucr_key))
                    if isinstance(relation_data, dict) and relation_data.get(D_UCR_ID):
                        existing_ucr_ids.add(str(relation_data[D_UCR_ID]))

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
        """Create a new cluster entry or merge users into an existing one."""

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

        existing_relations = existing_entry.data.get(D_RELATIONS_KEY, {})
        if not isinstance(existing_relations, dict):
            existing_relations = {}

        merged_relations = {
            **existing_relations,
            **new_relations,
        }

        if merged_relations == existing_relations:
            return self.async_abort(reason="already_configured")

        merged_data = {
            **existing_entry.data,
            D_CLUSTER_ID: self.final_entry.get(
                D_CLUSTER_ID, existing_entry.data.get(D_CLUSTER_ID)
            ),
            D_CLUSTER_NAME: self.final_entry.get(
                D_CLUSTER_NAME,
                existing_entry.data.get(D_CLUSTER_NAME),
            ),
            D_BASE_API_URL: self.final_entry.get(
                D_BASE_API_URL,
                existing_entry.data.get(D_BASE_API_URL, BASE_API_URL),
            ),
            D_UPDATE_INTERVAL_DATA: self.final_entry.get(
                D_UPDATE_INTERVAL_DATA,
                existing_entry.data.get(D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA),
            ),
            D_UPDATE_INTERVAL_ALARM: self.final_entry.get(
                D_UPDATE_INTERVAL_ALARM,
                existing_entry.data.get(
                    D_UPDATE_INTERVAL_ALARM,
                    UPDATE_INTERVAL_ALARM,
                ),
            ),
            D_USE_WEBHOOKS: self.final_entry.get(
                D_USE_WEBHOOKS,
                existing_entry.data.get(D_USE_WEBHOOKS, False),
            ),
            D_INTEGRATION_VERSION: self.final_entry.get(
                D_INTEGRATION_VERSION,
                existing_entry.data.get(D_INTEGRATION_VERSION),
            ),
            D_RELATIONS_KEY: merged_relations,
        }

        LOGGER.debug(
            "Merging %s user relation(s) into existing cluster '%s'",
            len(new_relations),
            selected_cluster_id,
        )

        return self.async_update_reload_and_abort(
            existing_entry,
            data_updates=merged_data,
        )

    async def _create_cluster(self) -> ConfigFlowResult:
        """Process device creation.

        Returns:
            ConfigFlowResult: The result of the config flow step "configure".

        """

        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        selected_cluster_id = self.final_entry.get(D_CLUSTER_ID)

        await self.async_set_unique_id(selected_cluster_id)
        # self._abort_if_unique_id_configured()

        # if webhook option enabled, try to set up webhook and show info or error before creating the entry
        if self.final_entry.get(D_USE_WEBHOOKS):
            if self.webhook_handler is None:
                self.webhook_handler = WebhookHandler(self)
            return await self.webhook_handler.prepare_webhook_entry(self.final_entry)

        return self.async_create_entry(
            title=self.final_entry[D_CLUSTER_NAME],
            data=self.final_entry,
        )

    async def _reconfigure_cluster(self) -> ConfigFlowResult:
        """Process device reconfiguration.

        Returns:
            ConfigFlowResult: The result of the config flow step "reconfigure".

        """

        if self.final_entry is None:
            return self.async_abort(reason="no_new_hubs_found")

        # if webhook option enabled, try to set up webhook and show info or error before creating the entry
        _old_use_webhook = self.reconf_config_entry.data.get(D_USE_WEBHOOKS)
        _new_use_webhook = self.final_entry.get(D_USE_WEBHOOKS)

        if self.final_entry.get(D_USE_WEBHOOKS) and (
            _old_use_webhook != _new_use_webhook
        ):
            if self.webhook_handler is None:
                self.webhook_handler = WebhookHandler(self)
            return await self.webhook_handler.prepare_webhook_entry(self.final_entry)

        return self.async_update_reload_and_abort(
            self.reconf_config_entry,
            data_updates=self.final_entry,
        )
