"""Config flow for myDivera integration."""

from collections.abc import Callable
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    D_API_KEY,
    D_CLUSTER_NAME,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERGROUP_ID,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
    VERSION,
)
from .divera_credentials import DiveraCredentials as dc
from .utils import get_translation

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

        if user_input is None:
            return self.async_show_menu(menu_options=["login", "api_key"])

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

        entry_id = self.context.get("entry_id")
        if not entry_id:
            return self.async_abort(reason="missing_entry_id")

        existing_entry = self.hass.config_entries.async_get_entry(entry_id)
        if not existing_entry:
            return self.async_abort(reason="hub_not_found")

        current_interval_data: int = existing_entry.data.get(
            D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
        )
        current_interval_alarm: int = existing_entry.data.get(
            D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
        )
        current_api_key: str = existing_entry.data.get(D_API_KEY, "")

        if user_input is None:
            return self._show_reconfigure_form(
                current_interval_data,
                current_interval_alarm,
                current_api_key,
            )

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

    async def _validate_and_proceed(
        self,
        validation_method: Callable,
        user_input: dict[str, Any],
    ) -> ConfigFlowResult:
        """Validate user input and decide next steps.

        Args:
            validation_method (callable): The calidation method to be used.
            user_input (dict[str, Any]): The user input data of step "reconfigure".

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        self.errors.clear()

        self.update_interval_data = user_input[D_UPDATE_INTERVAL_DATA]
        self.update_interval_alarm = user_input[D_UPDATE_INTERVAL_ALARM]

        self.errors, self.clusters = await validation_method(
            self.errors, self.session, user_input
        )

        if self.errors:
            return self._show_api_key_form()

        # check and delete dubliucate clusters
        self._handle_duplicates()

        if len(self.clusters) > 1:
            return self._show_multi_cluster_form()

        return await self._process_clusters()

    def _show_login_form(self) -> ConfigFlowResult:
        """Display the login input form.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): TextSelector(
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
                    D_UPDATE_INTERVAL_DATA, default=UPDATE_INTERVAL_DATA
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
                vol.Required(
                    D_UPDATE_INTERVAL_ALARM, default=UPDATE_INTERVAL_ALARM
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
            }
        )

        return self.async_show_form(
            step_id="login",
            data_schema=data_schema,
            errors=self.errors,
        )

    def _show_api_key_form(self) -> ConfigFlowResult:
        """Display the API key input form.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        data_schema = vol.Schema(
            {
                vol.Required(D_API_KEY): TextSelector(
                    TextSelectorConfig(type="password")  # type: ignore[misc]
                ),
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
        self,
        interval_data: int,
        interval_alarm: int,
        api_key: str,
    ) -> ConfigFlowResult:
        """Display the reconfigure input form.

        Args:
            interval_data (int): data update interval in case of no alarm.
            interval_alarm (int): data update interval in case of alarm.
            api_key (str): The API key to access Divera API.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        data_schema = vol.Schema(
            {
                vol.Required(D_API_KEY, default=api_key): TextSelector(
                    TextSelectorConfig(type="password")  # type: ignore[misc]
                ),
                vol.Required(D_UPDATE_INTERVAL_DATA, default=interval_data): vol.All(
                    vol.Coerce(int), vol.Range(min=30)
                ),
                vol.Required(D_UPDATE_INTERVAL_ALARM, default=interval_alarm): vol.All(
                    vol.Coerce(int), vol.Range(min=10)
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

    async def _async_show_usergroup_message(
        self,
        cluster_name: str,
        ucr_id: int,
        usergroup_id: int,
    ) -> None:
        """Show persistant message based on usergroup_id and related issues and permissions.

        Args:
            cluster_name (str): The name of the cluster/unit.
            ucr_id (int): The user_cluster_relation ID to identify the Divera user.
            usergroup_id (int): The class-ID of the usergroup the user belongs to.

        """

        translation = await get_translation(self.hass, "common")

        base_message = (
            translation.get("component.diveracontrol.common.usergroup_message") or ""
        )
        base_message = base_message.format(cluster_name=cluster_name, ucr_id=ucr_id)

        detail_key = f"component.diveracontrol.common.usergroup_{usergroup_id}"
        detail_message = translation.get(detail_key)

        if detail_message is None:
            detail_message = (
                translation.get("component.diveracontrol.common.usergroup_unknown")
                or ""
            )
            detail_message.format(usergroup_id=usergroup_id)

        full_message = base_message + "\n\n" + detail_message

        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "DiveraControl",
                "message": full_message,
                "notification_id": "diveracontrol_success_permissions",
            },
        )

    async def _process_clusters(self) -> ConfigFlowResult:
        """Process device creation.

        Returns:
            ConfigFLowResult: The result of the config flow step "reconfigure".

        """

        if self.clusters:
            for ucr_id, cluster_data in self.clusters.items():
                cluster_name = cluster_data[D_CLUSTER_NAME]
                api_key = cluster_data[D_API_KEY]
                ucr_id = cluster_data[D_UCR_ID]
                usergroup_id = cluster_data[D_USERGROUP_ID]

                new_hub = {
                    D_UCR_ID: ucr_id,
                    D_CLUSTER_NAME: cluster_name,
                    D_API_KEY: api_key,
                    D_UPDATE_INTERVAL_DATA: self.update_interval_data,
                    D_UPDATE_INTERVAL_ALARM: self.update_interval_alarm,
                }

                await self._async_show_usergroup_message(
                    cluster_name, ucr_id, usergroup_id
                )

                return self.async_create_entry(title=cluster_name, data=new_hub)

        return self.async_abort(reason="no_new_hubs_found")
