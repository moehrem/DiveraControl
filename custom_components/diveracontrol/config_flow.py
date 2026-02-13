"""Config flow for myDivera integration."""

from collections.abc import Callable
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.webhook import async_generate_id, async_generate_url
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    BASE_API_URL,
    D_API_KEY,
    D_BASE_API_URL,
    D_CLUSTER_NAME,
    D_INTEGRATION_VERSION,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USE_WEBHOOKS,
    D_WEBHOOK_ID,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
    VERSION,
)
from .divera_credentials import DiveraCredentials as dc

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

        self.session = None
        self.errors: dict[str, str] = {}
        self.clusters: dict[str, dict[str, Any]] = {}
        self.usergroup_id = ""
        self.update_interval_data = ""
        self.update_interval_alarm = ""
        self.base_api_url = ""
        self.use_webhooks = False
        self.webhook_id = ""
        self.webhook_url = ""
        self._pending_entry: dict[str, Any] | None = None
        self._finalize_entry = False
        self._pending_reconfigure_entry_id: str | None = None
        self._pending_reconfigure_data: dict[str, Any] | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step for user configuration.

        Args:
            user_input: The user input data of step "user".

        Returns:
            ConfigFLowResult: The result of the config flow step "user".

        """

        self.session = async_get_clientsession(self.hass)

        # Show a small form at the entry instead of a menu. Using a form
        # allows us to present errors on the same screen when validation
        # fails and to keep a consistent UI.
        if user_input is None:
            return self._show_entry_form()

        # choose next step depending on user selection
        method = user_input.get("method")
        if method == "login":
            return await self.async_step_login()
        if method == "api_key":
            return await self.async_step_api_key()

        return self.async_abort(reason="unknown_step")

    async def async_step_login(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle user login step.

        Args:
            user_input: The user input data of step "login".

        Returns:
            ConfigFLowResult: The result of the config flow step "login".

        """

        if user_input is None:
            return self._show_login_form()

        return await self._validate_and_proceed(dc.validate_login, user_input)

    async def async_step_api_key(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the API key input step.

        Args:
            user_input: The user input data of step "api_key".

        Returns:
            ConfigFLowResult: The result of the config flow step "api_key".

        """

        if user_input is None:
            return self._show_api_key_form()

        return await self._validate_and_proceed(dc.validate_api_key, user_input)

    async def async_step_webhook_info(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show webhook URL information before finishing setup."""

        if not self.use_webhooks:
            return self.async_abort(reason="unknown_step")

        is_reconfigure = self._pending_reconfigure_data is not None
        if not is_reconfigure and not self._pending_entry:
            return self.async_abort(reason="unknown_step")

        if user_input is None:
            return self.async_show_form(
                step_id="webhook_info",
                data_schema=vol.Schema({}),
                description_placeholders={"webhook_url": self.webhook_url},
                errors=self.errors,
            )

        if is_reconfigure:
            assert self._pending_reconfigure_data is not None
            assert self._pending_reconfigure_entry_id is not None
            self._pending_reconfigure_data[D_WEBHOOK_ID] = self.webhook_id
            data_updates = self._pending_reconfigure_data
            entry_id = self._pending_reconfigure_entry_id
            self._pending_reconfigure_data = None
            self._pending_reconfigure_entry_id = None
            return self.async_update_reload_and_abort(
                self.hass.config_entries.async_get_entry(entry_id),
                data_updates=data_updates,
            )

        self._pending_entry[D_WEBHOOK_ID] = self.webhook_id
        self._finalize_entry = True
        return await self._process_clusters()

    async def async_step_webhook_error(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show webhook URL error before finishing setup."""

        is_reconfigure = self._pending_reconfigure_data is not None
        if not is_reconfigure and not self._pending_entry:
            return self.async_abort(reason="unknown_step")

        if user_input is None:
            return self.async_show_form(
                step_id="webhook_error",
                data_schema=vol.Schema({}),
                errors=self.errors,
            )

        if is_reconfigure:
            assert self._pending_reconfigure_data is not None
            assert self._pending_reconfigure_entry_id is not None
            self._pending_reconfigure_data[D_USE_WEBHOOKS] = False
            self._pending_reconfigure_data.pop(D_WEBHOOK_ID, None)
            data_updates = self._pending_reconfigure_data
            entry_id = self._pending_reconfigure_entry_id
            self._pending_reconfigure_data = None
            self._pending_reconfigure_entry_id = None
            return self.async_update_reload_and_abort(
                self.hass.config_entries.async_get_entry(entry_id),
                data_updates=data_updates,
            )

        self._finalize_entry = True
        return await self._process_clusters()

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
            return self._show_multi_cluster_form()

        selected_clusters = user_input["clusters"]

        self.clusters = {
            ucr_id: cluster_data
            for ucr_id, cluster_data in self.clusters.items()
            if cluster_data[D_CLUSTER_NAME] in selected_clusters
        }

        return await self._process_clusters()

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing hub.

        Args:
            user_input: The user input data of step "reconfigure".

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        entry_id: str = self.context["entry_id"]
        config_entry: ConfigEntry = self.hass.config_entries.async_get_entry(entry_id)

        current_interval_data: int = config_entry.data.get(
            D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
        )
        current_interval_alarm: int = config_entry.data.get(
            D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
        )
        current_api_key: str = config_entry.data.get(D_API_KEY, "")
        current_base_api_url: str = config_entry.data.get(D_BASE_API_URL, BASE_API_URL)
        current_use_webhooks: bool = config_entry.data.get(D_USE_WEBHOOKS, False)

        if user_input is None:
            return self._show_reconfigure_form(
                current_interval_data,
                current_interval_alarm,
                current_api_key,
                current_base_api_url,
                current_use_webhooks,
            )

        new_api_key = user_input[D_API_KEY]
        new_interval_data = user_input[D_UPDATE_INTERVAL_DATA]
        new_interval_alarm = user_input[D_UPDATE_INTERVAL_ALARM]
        new_base_api_url = user_input[D_BASE_API_URL]
        new_use_webhooks = user_input[D_USE_WEBHOOKS]

        new_data = {
            **config_entry.data,
            D_API_KEY: new_api_key,
            D_UPDATE_INTERVAL_DATA: new_interval_data,
            D_UPDATE_INTERVAL_ALARM: new_interval_alarm,
            D_BASE_API_URL: new_base_api_url,
            D_USE_WEBHOOKS: new_use_webhooks,
        }

        if not new_use_webhooks:
            new_data.pop(D_WEBHOOK_ID, None)

        if new_use_webhooks and not current_use_webhooks:
            try:
                self.webhook_id = async_generate_id()
                # self.webhook_url = async_generate_url(
                #     self.hass, self.webhook_id, allow_internal=False
                # )
                self.webhook_url = (
                    get_url(
                        self.hass,
                        allow_internal=False,
                        allow_cloud=True,
                        prefer_cloud=True,
                    ).rstrip("/")
                    + f"/api/webhook/{self.webhook_id}"
                )

                self._pending_reconfigure_entry_id = entry_id
                self._pending_reconfigure_data = new_data
                self.use_webhooks = new_use_webhooks
                return await self.async_step_webhook_info()
            except NoURLAvailableError:
                LOGGER.error("No external URL configured for webhooks")
                self.errors["base"] = "no_external_url"
                self._pending_reconfigure_entry_id = entry_id
                self._pending_reconfigure_data = new_data
                return await self.async_step_webhook_error()

        return self.async_update_reload_and_abort(
            config_entry,
            data_updates=new_data,
        )

    async def _validate_and_proceed(
        self,
        validation_method: Callable[[dict[str, str], Any, dict[str, Any]], Any],
        user_input: dict[str, Any],
    ) -> ConfigFlowResult:
        """Validate user input and decide next steps.

        Args:
            validation_method (callable): The validation method to be used, might be `dc.validate_login` or `dc.validate_api_key`.
            user_input (dict[str, Any]): The user input data of step "reconfigure".

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        self.errors.clear()

        # persist non-sensitive input so we can prefill forms if the user
        # returns to the menu after validation errors
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

        # still update the working values used for processing
        self.update_interval_data = user_input.get(
            D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
        )
        self.update_interval_alarm = user_input.get(
            D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
        )
        self.base_api_url = user_input.get(D_BASE_API_URL, BASE_API_URL)
        self.use_webhooks = user_input.get(D_USE_WEBHOOKS, False)

        self.errors, self.clusters = await validation_method(
            self.errors, self.session, user_input, self.base_api_url
        )

        # error handling: show the initial menu so the user can switch
        # between login and API key flow if validation failed
        if self.errors:
            return self._show_entry_form(errors=self.errors)

        # check and delete duplicate clusters
        self._handle_duplicates()

        # if more units available, ask user to choose a unit
        if len(self.clusters) > 1:
            return self._show_multi_cluster_form()

        return await self._process_clusters()

    def _show_login_form(self) -> ConfigFlowResult:
        """Display the login input form.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        defaults = getattr(self, "_saved_login", {})

        self.errors.clear()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.EMAIL, autocomplete="username"
                    )
                ),
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD, autocomplete="current-password"
                    )
                ),
                vol.Required(
                    D_UPDATE_INTERVAL_DATA,
                    default=defaults.get(D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA),
                ): vol.All(vol.Coerce(int), vol.Range(min=5)),
                vol.Required(
                    D_UPDATE_INTERVAL_ALARM,
                    default=defaults.get(
                        D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5)),
                vol.Required(
                    D_BASE_API_URL, default=defaults.get(D_BASE_API_URL, BASE_API_URL)
                ): str,
                vol.Required(
                    D_USE_WEBHOOKS,
                    default=defaults.get(D_USE_WEBHOOKS, False),
                ): BooleanSelector(BooleanSelectorConfig()),
            }
        )

        return self.async_show_form(
            step_id="login",
            data_schema=data_schema,
            errors=self.errors,
        )

    def _show_entry_form(
        self, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Show the initial entry form (replaces menu) so errors can be displayed."""

        data_schema = vol.Schema(
            {
                vol.Required("method", default="login"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            "login",
                            "api_key",
                        ],
                        translation_key="entry_method_options",
                        multiple=False,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors or {}
        )

    def _show_api_key_form(self) -> ConfigFlowResult:
        """Display the API key input form.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        defaults = getattr(self, "_saved_api_key", {})

        self.errors.clear()

        data_schema = vol.Schema(
            {
                vol.Required(
                    D_API_KEY, default=defaults.get(D_API_KEY, "")
                ): TextSelector(
                    TextSelectorConfig(type="password")  # type: ignore[misc]
                ),
                vol.Required(
                    D_UPDATE_INTERVAL_DATA,
                    default=defaults.get(D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA),
                ): vol.All(vol.Coerce(int), vol.Range(min=5)),
                vol.Required(
                    D_UPDATE_INTERVAL_ALARM,
                    default=defaults.get(
                        D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5)),
                vol.Required(
                    D_BASE_API_URL, default=defaults.get(D_BASE_API_URL, BASE_API_URL)
                ): str,
                vol.Required(
                    D_USE_WEBHOOKS,
                    default=defaults.get(D_USE_WEBHOOKS, False),
                ): BooleanSelector(BooleanSelectorConfig()),
            }
        )

        return self.async_show_form(
            step_id=D_API_KEY,
            data_schema=data_schema,
            errors=self.errors,
        )

    def _show_reconfigure_form(
        self,
        interval_data: int,
        interval_alarm: int,
        api_key: str,
        base_api_url: str,
        use_webhooks: bool,
    ) -> ConfigFlowResult:
        """Display the reconfigure input form.

        Args:
            interval_data (int): data update interval in case of no alarm.
            interval_alarm (int): data update interval in case of alarm.
            api_key (str): The API key to access Divera API.
            base_api_url (str): The base API URL for Divera API.
            use_webhooks (bool): Whether to use webhooks for updates.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        data_schema = vol.Schema(
            {
                vol.Required(D_API_KEY, default=api_key): TextSelector(
                    TextSelectorConfig(type="password")  # type: ignore[misc]
                ),
                vol.Required(D_UPDATE_INTERVAL_DATA, default=interval_data): vol.All(
                    vol.Coerce(int), vol.Range(min=5)
                ),
                vol.Required(D_UPDATE_INTERVAL_ALARM, default=interval_alarm): vol.All(
                    vol.Coerce(int), vol.Range(min=5)
                ),
                vol.Required(D_BASE_API_URL, default=base_api_url): str,
                vol.Required(D_USE_WEBHOOKS, default=use_webhooks): BooleanSelector(
                    BooleanSelectorConfig()
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=self.errors,
        )

    def _show_multi_cluster_form(self) -> ConfigFlowResult:
        """Display the multi-cluster input form.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        cluster_names = [cluster[D_CLUSTER_NAME] for cluster in self.clusters.values()]

        cluster_schema = vol.Schema(
            {
                vol.Required("clusters", default=cluster_names[0]): SelectSelector(
                    SelectSelectorConfig(options=cluster_names, multiple=False)
                )
            }
        )

        return self.async_show_form(
            step_id="multi_cluster",
            data_schema=cluster_schema,
            errors=self.errors,
        )

    def _handle_duplicates(self) -> None:
        """Mark for removal if duplicate and remove duplicates from the clusters dict.

        Returns:
            None

        """

        clusters_to_remove = []

        # checking for existing cluster and mark for removal if duplicate
        for ucr_id, cluster_data in self.clusters.items():
            cluster_name = cluster_data[D_CLUSTER_NAME]

            for entry in self._async_current_entries():
                existing_ucr_id = entry.data.get(D_UCR_ID)

                if existing_ucr_id == ucr_id or entry.title == cluster_name:
                    LOGGER.debug(
                        "Skipping duplicate hub creation for '%s' (ID: %s)",
                        cluster_name,
                        ucr_id,
                    )
                    clusters_to_remove.append(ucr_id)
                    continue

        # remove duplicates
        for ucr_id in clusters_to_remove:
            del self.clusters[ucr_id]

    async def _process_clusters(self) -> ConfigFlowResult:
        """Process device creation.

        Returns:
            ConfigFlowResult: The result of the config flow step "reconfigure".

        """

        if self._pending_entry and self._finalize_entry:
            new_entry = self._pending_entry
            self._pending_entry = None
            self._finalize_entry = False
            return self.async_create_entry(
                title=new_entry[D_CLUSTER_NAME],
                data=new_entry,
            )

        if self.clusters:
            for ucr_id, cluster_data in self.clusters.items():
                cluster_name: str = cluster_data[D_CLUSTER_NAME]
                api_key: str = cluster_data[D_API_KEY]
                ucr_id: int = cluster_data[D_UCR_ID]

                new_entry: dict[str, Any] = {
                    D_UCR_ID: ucr_id,
                    D_CLUSTER_NAME: cluster_name,
                    D_API_KEY: api_key,
                    D_BASE_API_URL: self.base_api_url,
                    D_UPDATE_INTERVAL_DATA: self.update_interval_data,
                    D_UPDATE_INTERVAL_ALARM: self.update_interval_alarm,
                    D_USE_WEBHOOKS: self.use_webhooks,
                    D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
                }

                if self.use_webhooks:
                    try:
                        self.webhook_id = async_generate_id()
                        # self.webhook_url = async_generate_url(
                        #     self.hass, self.webhook_id, allow_internal=False
                        # )
                        self.webhook_url = (
                            get_url(
                                self.hass,
                                allow_internal=False,
                                allow_cloud=True,
                                prefer_cloud=True,
                            ).rstrip("/")
                            + f"/api/webhook/{self.webhook_id}"
                        )
                        self._pending_entry = new_entry
                        return await self.async_step_webhook_info()

                    except NoURLAvailableError:
                        LOGGER.error("No external URL configured for webhooks")
                        self.errors["base"] = "no_external_url"
                        new_entry[D_USE_WEBHOOKS] = False
                        new_entry.pop(D_WEBHOOK_ID, None)
                        self._pending_entry = new_entry
                        return await self.async_step_webhook_error()

                return self.async_create_entry(title=cluster_name, data=new_entry)

        return self.async_abort(reason="no_new_hubs_found")
