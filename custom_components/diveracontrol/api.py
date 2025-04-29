"""Communication with Divera 24/7 api."""

import logging

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_ACCESS_KEY,
    API_ALARM,
    API_AUTH_LOGIN,
    API_MESSAGES,
    API_PULL_ALL,
    API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    API_USING_VEHICLE_SET_SINGLE,
    BASE_API_URL,
    BASE_API_V2_URL,
    D_API_KEY,
    D_CLUSTER_NAME,
    D_DATA,
    D_NAME,
    D_UCR,
    D_UCR_ID,
    D_USERGROUP_ID,
    PERM_ALARM,
    PERM_MESSAGES,
    PERM_STATUS_VEHICLE,
)
from .utils import log_execution_time, permission_check

LOGGER = logging.getLogger(__name__)


class DiveraAPI:
    """Class to interact with the Divera 24/7 API."""

    def __init__(self, hass: HomeAssistant, ucr_id: str, api_key: str) -> None:
        """Initialize the API client."""
        self.api_key = api_key
        self.ucr_id = ucr_id
        self.hass = hass

        self.session = async_get_clientsession(hass)

    @log_execution_time
    async def api_request(
        self,
        url: str,
        method: str,
        parameters: dict | None = None,
        payload: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        """Request data from Divera API at the given endpoint.

        Args:
            url (str): URL to request.
            method (str): HTTP method to use. Defaults to "GET".
            perm_key (str): Permission key to check if user is allowed to enter API. Special: All non-restricted APIs have "perm_key=None"
            parameters (dict | None): Dictionary containing URL parameters. Defaults to None.
            payload (dict | None): JSON payload for the request. Defaults to None.
            headers (dict | None): HTTP headers. Defaults to `{ "Accept": "*/*", "Content-Type": "application/json"}`.

        Returns:
            dict: JSON response from the API.

        """
        # init headers, if None
        headers = headers or {
            "Accept": "*/*",
            "Content-Type": "application/json",
        }

        # init "parameters" as dict, if None; add mandatory api-key
        parameters = parameters or {}
        parameters[API_ACCESS_KEY] = self.api_key

        # Add parameters to the URL
        if parameters:
            param_strings = [f"{key}={value}" for key, value in parameters.items()]
            param_string = "&".join(param_strings)
            url = f"{url}?{param_string}"

        try:
            log_url = url.replace(self.api_key, "**REDACTED**")
            LOGGER.debug("Starting request to Divera API: %s", log_url)

            async with self.session.request(
                method, url, json=payload, headers=headers, timeout=10
            ) as response:
                if response.status != 200:
                    raise ConfigEntryNotReady(
                        f"Divera API not ready (status {response.status}) for cluster id '{self.ucr_id}'"
                    )

                if response.status == 200:
                    try:
                        LOGGER.debug("Finished request to Divera API: %s", log_url)
                        return await response.json()
                    except Exception:
                        LOGGER.exception("Error parsing JSON response from Divera API")
                        return response

                return {}
        except ClientError as e:
            log_url = url.replace(self.api_key, "**REDACTED**")
            LOGGER.error(
                "Client error: %s for cluster id %s from url %s",
                e,
                self.ucr_id,
                log_url,
            )
            return {}

    async def get_ucr_data(self, ucr_id) -> dict:
        """GET all data for user cluster relation from the Divera API. No permission check."""
        LOGGER.debug("Fetching all data for cluster %s", self.ucr_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
        method = "GET"
        parameters = {D_UCR: ucr_id}
        return await self.api_request(url, method, parameters=parameters)

    async def post_vehicle_status(self, vehicle_id, payload) -> dict:
        """POST vehicle status and data to Divera API."""
        LOGGER.debug("Posting vehicle status and data for cluster %s", self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}"
            method = "POST"
            return await self.api_request(url, method, payload=payload)

        return False

    async def post_alarms(self, payload) -> dict:
        """POST new alarm to Divera API."""
        LOGGER.debug("Posting alarms for unit %s", self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_ALARM):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}"
            method = "POST"
            return await self.api_request(url, method, payload=payload)

        return False

    async def put_alarms(self, payload, alarm_id) -> dict:
        """PUT changes for existing alarm to Divera API."""
        LOGGER.debug(
            "Putting changes to alarm %s for cluster %s", alarm_id, self.ucr_id
        )

        if permission_check(self.hass, self.ucr_id, PERM_ALARM):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/{alarm_id}"
            method = "PUT"
            return await self.api_request(url, method, payload=payload)

        return False

    async def post_close_alarm(self, payload, alarm_id) -> dict:
        """POSt to close an existing alarm to Divera API."""
        LOGGER.debug("Posting to close alarm %s for cluster %s", alarm_id, self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_ALARM):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}"
            method = "POST"
            return await self.api_request(url, method, payload=payload)

        return False

    async def post_message(self, payload) -> dict:
        """POSt to close an existing alarm to Divera API."""
        LOGGER.debug("Posting message for cluster %s", self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_MESSAGES):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_MESSAGES}"
            method = "POST"
            return await self.api_request(url, method, payload=payload)

        return False

    async def get_vehicle_property(self, vehicle_id) -> dict:
        """GET individual vehicle poroperties for vehicle from Divera API."""
        LOGGER.debug(
            "Getting individual vehicle properties for vehicle id %s", vehicle_id
        )

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}"
            method = "GET"
            return await self.api_request(url, method)

        return False

    async def post_using_vehicle_property(self, payload, vehicle_id) -> dict:
        """POST individual vehicle poroperties for vehicle from Divera API."""
        LOGGER.debug(
            "Posting individual vehicle properties for cluster %s", self.ucr_id
        )

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/set/{vehicle_id}"
            method = "POST"
            return await self.api_request(url, method, payload=payload)

        return False

    async def post_using_vehicle_crew(self, payload, vehicle_id, mode) -> dict:
        """POST add one or more crew to a vehicle."""
        LOGGER.debug(
            "Posting %s crew members to vehicle %s for cluster %s",
            mode,
            vehicle_id,
            self.ucr_id,
        )

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_CREW}/{mode}/{vehicle_id}"
            method = "POST"
            return await self.api_request(url, method, payload=payload)

        return False


class DiveraCredentials:
    """Validates Divera credentials: username, password, api-key."""

    @staticmethod
    async def fetch_cluster_data(session, url_ucr, api_key, ucr_id):
        """Fetch cluster data for ucr_id."""
        try:
            async with session.get(url_ucr, timeout=10) as response:
                data_ucr_response = await response.json()

                if not data_ucr_response.get("success") or response.status not in [
                    200,
                    201,
                ]:
                    return None, data_ucr_response.get("message", {})

                data_ucr_data = data_ucr_response.get(D_DATA, {}).get(D_UCR, {})
                cluster_name = data_ucr_data.get(ucr_id, {}).get(D_NAME, "")
                usergroup_id = data_ucr_data.get(ucr_id, {}).get(D_USERGROUP_ID, "")

                return (
                    {
                        D_CLUSTER_NAME: cluster_name,
                        D_UCR_ID: ucr_id,
                        D_API_KEY: api_key,
                    },
                    None,
                    usergroup_id,
                )

        except (ClientError, TimeoutError):
            return None, "cannot_connect"
        except (TypeError, AttributeError):
            return None, "no_data"
        except Exception:
            LOGGER.exception("Error fetching cluster data")
            return None, "unknown"

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
            errors["base"] = e
            return errors, clusters

    @staticmethod
    async def validate_api_key(
        errors: dict[str, str],
        session: dict,
        user_input: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, str], str]:
        """Validate API access and fetch all instance names.

        Args:
            errors (dict): Dictionary with error messages.
            session (dict): Valid websession of Hass.
            user_input (dict): User input, most likely from config_flow.

        Returns:
            errors (dict): Dictionary with error messages.
            cluster (dict): Mapping of hub IDs to their names.
            api_key (str): Retrieved API key.

        """
        clusters = {}
        errors = {}
        api_key = user_input.get("api_key", "")
        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}?{API_ACCESS_KEY}={api_key}"
        )

        try:
            async with session.get(url, timeout=10) as response:
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
            errors["base"] = e

        return errors, clusters
