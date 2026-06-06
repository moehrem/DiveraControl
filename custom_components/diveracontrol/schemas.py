"""Form schemas for DiveraControl config flow."""

from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    BASE_API_URL,
    D_API_KEY,
    D_BASE_API_URL,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERNAME,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
)


def get_entry_form_schema() -> vol.Schema:
    """Get the initial entry form schema.

    Returns:
        vol.Schema: The form schema for initial entry method selection.

    """

    return vol.Schema(
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


def get_login_form_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get the login form schema.

    Args:
        defaults: Dictionary with default values for form fields.

    Returns:
        vol.Schema: The form schema for login.

    """

    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
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
                default=defaults.get(D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Required(
                D_BASE_API_URL, default=defaults.get(D_BASE_API_URL, BASE_API_URL)
            ): str,
        }
    )


def get_api_key_form_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get the API key form schema.

    Args:
        defaults: Dictionary with default values for form fields.

    Returns:
        vol.Schema: The form schema for API key authentication.

    """

    return vol.Schema(
        {
            vol.Required(D_API_KEY, default=defaults.get(D_API_KEY, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(
                D_UPDATE_INTERVAL_DATA,
                default=defaults.get(D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Required(
                D_UPDATE_INTERVAL_ALARM,
                default=defaults.get(D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Required(
                D_BASE_API_URL, default=defaults.get(D_BASE_API_URL, BASE_API_URL)
            ): str,
        }
    )


def get_options_form_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get the options form schema for editable cluster settings."""

    return vol.Schema(
        {
            vol.Required(
                D_UPDATE_INTERVAL_DATA,
                default=defaults.get(D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Required(
                D_UPDATE_INTERVAL_ALARM,
                default=defaults.get(D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Required(
                D_BASE_API_URL, default=defaults.get(D_BASE_API_URL, BASE_API_URL)
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="url")
            ),
        }
    )


def get_reconfigure_ucr_form_schema(selected_ucr: dict[str, Any]) -> vol.Schema:
    """Get the reconfigure form schema for user cluster relations.

    Args:
        selected_ucr: Dictionary of the selected user cluster relation.

    Returns:
        vol.Schema: The form schema for reconfiguration of user cluster relations.
    """

    return vol.Schema(
        {
            vol.Required(
                D_USERNAME, default=selected_ucr.get(D_USERNAME, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                D_API_KEY, default=selected_ucr.get(D_API_KEY, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Required(
                D_BASE_API_URL,
                default=selected_ucr.get(D_BASE_API_URL, BASE_API_URL),
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="url")
            ),
            vol.Required(
                D_UPDATE_INTERVAL_DATA,
                default=selected_ucr.get(D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Required(
                D_UPDATE_INTERVAL_ALARM,
                default=selected_ucr.get(
                    D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
        }
    )


def get_reconfigure_cluster_form_schema(
    current_ucrs: dict[str, dict[str, Any]],
) -> vol.Schema:
    """Get the reconfigure form schema.

    Args:
        current_ucrs: Dictionary of current user cluster relations.

    Returns:
        vol.Schema: The form schema for reconfiguration.

    """

    options: list[dict[str, str]] = []
    for ucr_id, ucr in current_ucrs.items():
        username = str(ucr.get(D_USERNAME, "")).strip() or str(ucr_id)
        options.append({"value": str(ucr_id), "label": username})

    if not options:
        options = [{"value": "", "label": ""}]

    return vol.Schema(
        {
            vol.Required(D_UCR_ID, default=options[0]["value"]): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    multiple=False,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def get_multi_cluster_form_schema(cluster_names: list[str]) -> vol.Schema:
    """Get the multi-cluster form schema.

    Args:
        cluster_names: List of available cluster names.

    Returns:
        vol.Schema: The form schema for cluster selection.

    """

    return vol.Schema(
        {
            vol.Required("clusters", default=cluster_names[0]): SelectSelector(
                SelectSelectorConfig(options=cluster_names, multiple=False)
            )
        }
    )
