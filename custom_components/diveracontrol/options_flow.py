"""Options flow for DiveraControl integration."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, OptionsFlow, ConfigFlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    BASE_API_URL,
    D_API_KEY,
    D_BASE_API_URL,
    D_CLUSTER_NAME,
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERNAME,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
    BASE_API_URL as DEFAULT_BASE_API_URL,
)
from .schemas import get_options_form_schema, get_reconfigure_cluster_form_schema


class DiveraControlOptionsFlow(OptionsFlow):
    """Handle options flow for DiveraControl integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._selected_ucr_id: str | None = None

    def _cluster_name(self) -> str:
        """Return cluster name placeholder value."""
        return self._config_entry.data.get(D_CLUSTER_NAME, "DiveraControl")

    def _relations(self) -> dict[str, dict[str, Any]]:
        """Return normalized user relations from config entry data."""
        relations = self._config_entry.data.get(D_RELATIONS_KEY, {})
        if not isinstance(relations, dict):
            return {}

        normalized_relations: dict[str, dict[str, Any]] = {}
        for raw_ucr_id, relation_data in relations.items():
            if not isinstance(relation_data, dict):
                continue
            ucr_id = str(raw_ucr_id)
            normalized_relations[ucr_id] = {
                **relation_data,
                D_UCR_ID: relation_data.get(D_UCR_ID, ucr_id),
            }

        return normalized_relations

    @staticmethod
    def _user_api_key_schema(selected_relation: dict[str, Any]) -> vol.Schema:
        """Return schema for updating one user's API key."""
        return vol.Schema(
            {
                vol.Required(
                    D_API_KEY,
                    default=selected_relation.get(D_API_KEY, ""),
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            }
        )

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["cluster_settings", "user_select"],
            description_placeholders={
                "cluster_name": self._cluster_name(),
            },
        )

    async def async_step_cluster_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage cluster-wide integration options."""
        if user_input is None:
            defaults = {
                D_UPDATE_INTERVAL_DATA: self._config_entry.data.get(
                    D_UPDATE_INTERVAL_DATA,
                    UPDATE_INTERVAL_DATA,
                ),
                D_UPDATE_INTERVAL_ALARM: self._config_entry.data.get(
                    D_UPDATE_INTERVAL_ALARM,
                    UPDATE_INTERVAL_ALARM,
                ),
                D_BASE_API_URL: self._config_entry.data.get(
                    D_BASE_API_URL,
                    BASE_API_URL,
                ),
            }
            return self.async_show_form(
                step_id="cluster_settings",
                data_schema=get_options_form_schema(defaults),
                description_placeholders={
                    "cluster_name": self._cluster_name(),
                },
            )

        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={
                **self._config_entry.data,
                D_UPDATE_INTERVAL_DATA: user_input[D_UPDATE_INTERVAL_DATA],
                D_UPDATE_INTERVAL_ALARM: user_input[D_UPDATE_INTERVAL_ALARM],
                D_BASE_API_URL: user_input[D_BASE_API_URL],
            },
        )
        await self.hass.config_entries.async_reload(self._config_entry.entry_id)
        return self.async_create_entry(title="", data={})

    async def async_step_user_select(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Select a user relation for API key update."""
        relations = self._relations()
        if not relations:
            return self.async_abort(reason="no_ucr")

        if user_input is None:
            return self.async_show_form(
                step_id="user_select",
                data_schema=get_reconfigure_cluster_form_schema(relations),
                description_placeholders={
                    "cluster_name": self._cluster_name(),
                },
            )

        self._selected_ucr_id = str(user_input[D_UCR_ID])
        return await self.async_step_user_api_key()

    async def async_step_user_api_key(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Update API key for the selected user relation."""
        if self._selected_ucr_id is None:
            return self.async_abort(reason="unknown_step")

        relations = self._relations()
        selected_relation = relations.get(self._selected_ucr_id)
        if selected_relation is None:
            return self.async_abort(reason="unknown_step")

        if user_input is None:
            return self.async_show_form(
                step_id="user_api_key",
                data_schema=self._user_api_key_schema(selected_relation),
                description_placeholders={
                    "cluster_name": self._cluster_name(),
                    "username": selected_relation.get(
                        D_USERNAME, self._selected_ucr_id
                    ),
                },
            )

        updated_relations = dict(relations)
        updated_relations[self._selected_ucr_id] = {
            **selected_relation,
            D_API_KEY: user_input[D_API_KEY],
        }

        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={
                **self._config_entry.data,
                D_RELATIONS_KEY: updated_relations,
            },
        )
        await self.hass.config_entries.async_reload(self._config_entry.entry_id)
        return self.async_create_entry(title="", data={})
