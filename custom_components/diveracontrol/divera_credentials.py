"""Checks for Divera credentials and API key."""

import logging

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    API_ACCESS_KEY,
    API_AUTH_LOGIN,
    API_PULL_ALL,
    BASE_API_URL,
    BASE_API_V2_URL,
    D_API_KEY,
    D_CLUSTER_NAME,
    D_DATA,
    D_NAME,
    D_UCR,
    D_UCR_ID,
    D_USERGROUP_ID,
)

LOGGER = logging.getLogger(__name__)


class DiveraCredentials:
    """Validates Divera credentials: username, password, api-key."""

    @staticmethod
    async def validate_login(
        errors: dict[str, str],
        session: ClientSession | None,
        user_input: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Validate login and fetch all instance names.

        Args:
            errors: Dictionary with error messages (not used, kept for compatibility).
            session: Valid websession of Home Assistant.
            user_input: User input from config flow containing username and password.

        Returns:
            Tuple of (errors dict, clusters dict) where clusters maps UCR IDs to their data.

        """
        clusters = {}
        url_auth = f"{BASE_API_URL}{BASE_API_V2_URL}{API_AUTH_LOGIN}"
        payload = {
            "Login": {
                "username": user_input.get("username", ""),
                "password": user_input.get("password", ""),
                "jwt": "false",
            }
        }

        try:
            async with session.post(
                url_auth, json=payload, timeout=ClientTimeout(total=10)
            ) as response:
                data_auth = await response.json()

                # Handle authentication failure
                if not data_auth.get("success"):
                    return DiveraCredentials._format_auth_errors(
                        data_auth.get("errors", {})
                    ), {}

                # Extract user and cluster data
                data_user = data_auth.get("data", {}).get("user", {})
                api_key = data_user.get("access_token", "")
                data_ucr = data_auth.get("data", {}).get("ucr", [])

                # Build clusters dictionary
                for cluster in data_ucr:
                    ucr_id = str(cluster.get("id", ""))
                    if ucr_id:  # Only add if we have a valid UCR ID
                        clusters[ucr_id] = {
                            D_CLUSTER_NAME: cluster.get(D_NAME, ""),
                            D_UCR_ID: ucr_id,
                            D_API_KEY: api_key,
                            D_USERGROUP_ID: cluster.get(D_USERGROUP_ID, ""),
                        }

                return {}, clusters

        except (ClientError, TimeoutError) as err:
            LOGGER.error("Connection error during login validation: %s", err)
            return {"base": "cannot_connect"}, {}
        except (TypeError, AttributeError) as err:
            LOGGER.error("Data parsing error during login validation: %s", err)
            return {"base": "no_data"}, {}
        except Exception:
            LOGGER.exception("Unexpected error during login validation")
            return {"base": "unknown"}, {}

    @staticmethod
    def _format_auth_errors(raw_errors: dict | list | str) -> dict[str, str]:
        """Format authentication errors into a standard dictionary.

        Args:
            raw_errors: Raw error data from API response.

        Returns:
            Dictionary with formatted error message under "base" key.

        """
        if isinstance(raw_errors, list):
            return {"base": "; ".join(str(err) for err in raw_errors)}

        if isinstance(raw_errors, dict):
            error_messages = []
            for value in raw_errors.values():
                if isinstance(value, str):
                    error_messages.append(value)
                elif isinstance(value, list):
                    error_messages.extend(str(item) for item in value)
                else:
                    error_messages.append(str(value))
            return {"base": "; ".join(error_messages)}

        return {"base": str(raw_errors)}

    @staticmethod
    async def validate_api_key(
        errors: dict[str, str],
        session: ClientSession,
        user_input: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Validate API access and fetch all instance names.

        Args:
            errors (dict): Dictionary with error messages.
            session (dict): Valid websession of Hass.
            user_input (dict): User input, most likely from config_flow.

        Returns:
            errors (dict): Dictionary with error messages.
            cluster (dict): Mapping of hub IDs to their names.

        """
        clusters = {}
        errors = {}
        api_key = user_input.get("api_key", "")
        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}?{API_ACCESS_KEY}={api_key}"
        )

        try:
            async with session.request(
                method="GET",
                url=url,
                timeout=ClientTimeout(total=10),
            ) as response:
                data = await response.json()

                if response.status not in [200, 201]:
                    errors["base"] = data.get("message", {})
                    return errors, clusters

                data_ucr = data.get(D_DATA, {}).get(D_UCR, {})

                for ucr_id, ucr_data in data_ucr.items():
                    clusters[ucr_id] = {
                        D_CLUSTER_NAME: ucr_data.get(D_NAME, ""),
                        D_UCR_ID: ucr_id,
                        D_API_KEY: api_key,
                        D_USERGROUP_ID: ucr_data.get(D_USERGROUP_ID, ""),
                    }

        except (ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except (TypeError, AttributeError):
            errors["base"] = "no_data"
        except Exception as e:
            errors["base"] = str(e)

        return errors, clusters
