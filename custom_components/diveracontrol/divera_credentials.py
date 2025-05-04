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
        session,
        user_input: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Validate login and fetch all instance names.

        Args:
            errors (dict): Dictionary with error messages.
            session (dict): Valid websession of Hass.
            user_input (dict): User input, most likely from config_flow.

        Returns:
            errors (dict): Dictionary with error messages.
            cluster (dict): Mapping of hub IDs to their names.

        """

        errors = {}
        clusters = {}
        api_key = ""
        data_ucr = {}

        url_auth = f"{BASE_API_URL}{BASE_API_V2_URL}{API_AUTH_LOGIN}"
        payload = {
            "Login": {
                "username": user_input.get("username", ""),
                "password": user_input.get("password", ""),
                "jwt": "false",
            }
        }

        # Login-Request
        try:
            async with session.post(url_auth, json=payload, timeout=10) as response:
                data_auth = await response.json()

                if not data_auth.get("success"):
                    raw_errors = data_auth.get("errors", {})
                    formatted_errors = {}

                    if isinstance(raw_errors, list):
                        formatted_errors["base"] = "; ".join(raw_errors)
                    elif isinstance(raw_errors, dict):
                        formatted_errors["base"] = "; ".join(
                            v if isinstance(v, str) else "; ".join(v)
                            for v in raw_errors.values()
                        )
                    else:
                        formatted_errors["base"] = str(raw_errors)

                    return formatted_errors, clusters

                data_user = data_auth.get("data", {}).get("user", {})
                api_key = data_user.get("access_token", "")
                data_ucr = data_auth.get("data", {}).get("ucr", {})

                for cluster in data_ucr:
                    ucr_id = cluster.get("id", "")
                    clusters[ucr_id] = {
                        D_CLUSTER_NAME: cluster.get(D_NAME, ""),
                        D_UCR_ID: ucr_id,
                        D_API_KEY: api_key,
                        D_USERGROUP_ID: cluster.get(D_USERGROUP_ID, ""),
                    }

                return errors, clusters

        except (ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
            return errors, clusters
        except (TypeError, AttributeError):
            errors["base"] = "no_data"
            return errors, clusters
        except Exception as e:
            errors["base"] = str(e)
            return errors, clusters

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
