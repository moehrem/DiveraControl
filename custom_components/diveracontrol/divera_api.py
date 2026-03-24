"""Communication with Divera 24/7 api."""

import logging
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_ACCESS_KEY,
    API_ALARM,
    API_AUTH_LOGIN,
    API_MESSAGES,
    API_NEWS,
    API_PULL_ALL,
    API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    API_USING_VEHICLE_SET_SINGLE,
    BASE_API_V2_URL,
    D_API_KEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_DATA,
    D_INTEGRATION_VERSION,
    D_NAME,
    D_RELATIONS_KEY,
    D_UCR,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USE_WEBHOOKS,
    D_USERGROUP_ID,
    MINOR_VERSION,
    PATCH_VERSION,
    PERM_ALARM,
    PERM_MESSAGES,
    PERM_NEWS,
    PERM_STATUS_VEHICLE,
    VERSION,
)
from .divera_permissions import DiveraPermissions

_LOGGER = logging.getLogger(__name__)


class DiveraAPI:
    """Class to interact with the Divera 24/7 API."""

    def __init__(
        self,
        hass: HomeAssistant,
        ucr_id: str,
        api_key: str,
        base_url: str,
    ) -> None:
        """Initialize the API client.

        Args:
            hass (HomeAssistant): Instance of HomeAssistant.
            ucr_id (str): user_cluster_relation, the ID to identify the Divera-user.
            api_key (str): API key to access Divera API.
            base_url (str): Base URL for the Divera API.

        Returns:
            None

        """
        self.api_key = api_key
        self.ucr_id = ucr_id
        self.hass = hass
        self.base_url = base_url
        self.permissions = DiveraPermissions()
        self.permissions.ucr_id = self.ucr_id

        self.session = async_get_clientsession(hass)

    def _redact_url(self, url: str) -> str:
        """Redact API key from URL for logging.

        Args:
            url: URL to redact.

        Returns:
            URL with API key replaced by asterisks.
        """
        return url.replace(self.api_key, "***")

    async def _api_request(
        self,
        part_url: str,
        method: str,
        payload: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Request data from Divera API at the given endpoint.

        Args:
            part_url (str): Part of the URL to access specific API endpoint.
            method (str): HTTP method to use for the request (GET, POST, etc.).
            payload (dict, optional): Data to send with the request. Defaults to None.

        Returns:
            dict: JSON response from the API.

        """

        # build full URL from base URL and part URL
        url = f"{self.base_url}{part_url}"

        # init headers
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
        }

        # init "parameters" as dict
        # IMPORTANT! Every API-call needs these two parameters: api_key and ucr_id
        # api_key is needed for authentification
        # ucr_id is needed to identify the divera unit - without that parameter Divera will accept the call for the main unit of the user only!
        parameters: dict[str, str] = {}
        parameters[API_ACCESS_KEY] = self.api_key
        parameters[D_UCR] = self.ucr_id
        url = f"{url}?{urlencode(parameters)}"

        _LOGGER.debug(
            "API request for cluster %s: %s %s",
            self.ucr_id,
            method,
            self._redact_url(url),
        )

        try:
            async with self.session.request(
                method,
                url,
                json=payload,
                headers=headers,
                timeout=ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()

                _LOGGER.debug(
                    "API response for cluster %s: %s",
                    self.ucr_id,
                    self._redact_url(url),
                )

                # this is needed, as https-response status could be OK, but Divera still returns "success" = false
                if data.get("success") is not True:
                    raise HomeAssistantError(f"Divera API error: {data.get('message')}")

                return data

        except ClientResponseError as err:
            if err.status == 401:
                raise ConfigEntryAuthFailed(
                    f"Invalid API key for cluster {self.ucr_id}"
                ) from err
            if err.status >= 500:
                raise ConfigEntryNotReady(
                    f"Divera API unavailable (HTTP {err.status})"
                ) from err
            raise HomeAssistantError(
                f"Divera API error (HTTP {err.status}): {err.message}"
            ) from err

        except TimeoutError as err:
            raise ConfigEntryNotReady(
                "Timeout connecting to Divera API after 10 seconds"
            ) from err

        except ClientError as err:
            request_url = getattr(getattr(err, "request_info", None), "real_url", None)
            url = self._redact_url(str(request_url)) if request_url else "unknown"
            raise HomeAssistantError(
                f"Failed to connect to Divera API at URL: {url}"
            ) from err

    async def close(self) -> None:
        """Cleanup if needed in the future - right now just implemented as a dummy to satisfy linting."""

    async def get_pull_all(
        self,
    ) -> dict[str, Any]:
        """GET all data for user cluster relation from the Divera API. No permission check.

        Args:
            ucr_id (str): user_cluster_relation, the ID to identify the Divera-user.

        Returns:
            dict: JSON response from the API.

        """
        _LOGGER.debug("Fetching all data for cluster %s", self.ucr_id)
        part_url = f"{BASE_API_V2_URL}{API_PULL_ALL}"
        method = "GET"
        data = await self._api_request(part_url, method)

        if data.get("success", False):
            self.permissions.replace_permissions_from_ucr_data(data)

        return data

    async def post_vehicle_status(
        self,
        vehicle_id: int,
        payload: dict[str, str],
    ) -> None:
        """POST vehicle status and data to Divera API.

        Args:
            vehicle_id (int): Divera-ID of the vehicle to update.
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug("Posting vehicle status and data for cluster %s", self.ucr_id)

        self.permissions.check(PERM_STATUS_VEHICLE)

        part_url = f"{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)

    async def post_alarms(
        self,
        payload: dict[str, str],
    ) -> None:
        """POST new alarm to Divera API.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug("Posting alarms for unit %s", self.ucr_id)

        self.permissions.check(PERM_ALARM)

        part_url = f"{BASE_API_V2_URL}{API_ALARM}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)

    async def put_alarms(
        self,
        alarm_id: int,
        payload: dict[str, str],
    ) -> None:
        """PUT changes for existing alarm to Divera API.

        Args:
            alarm_id (int): Divera-Alarm-ID which had to be changed.
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug(
            "Putting changes to alarm %s for cluster %s", alarm_id, self.ucr_id
        )

        self.permissions.check(PERM_ALARM)

        part_url = f"{BASE_API_V2_URL}{API_ALARM}/{alarm_id}"
        method = "PUT"

        await self._api_request(part_url, method, payload=payload)

    async def post_close_alarm(
        self,
        payload: dict[str, str],
        alarm_id: int,
    ) -> None:
        """POST to close an existing alarm to Divera API.

        Args:
            alarm_id (int): Divera-Alarm-ID which had to be changed.
            payload (dict): Dictionary of data to send to Divera-API.

        """

        _LOGGER.debug("Posting to close alarm %s for cluster %s", alarm_id, self.ucr_id)

        self.permissions.check(PERM_ALARM)

        part_url = f"{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)

    async def post_message(
        self,
        payload: dict[str, str],
    ) -> None:
        """POST to close an existing alarm to Divera API.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug("Posting message for cluster %s", self.ucr_id)

        self.permissions.check(PERM_MESSAGES)

        part_url = f"{BASE_API_V2_URL}{API_MESSAGES}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)

    async def get_vehicle_property(
        self,
        vehicle_id: int,
    ) -> dict[str, str]:
        """GET individual vehicle poroperties for vehicle from Divera API.

        Args:
            vehicle_id (int): ID of the vehicle to fetch property data from.

        Returns:
            dict: JSON response from the API, otherwise empty if no permissions.

        """
        _LOGGER.debug(
            "Getting individual vehicle properties for vehicle id %s", vehicle_id
        )

        self.permissions.check(PERM_STATUS_VEHICLE)

        part_url = f"{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}"
        method = "GET"

        return await self._api_request(part_url, method)

    async def post_using_vehicle_property(
        self,
        vehicle_id: int,
        payload: dict[str, str],
    ) -> None:
        """POST individual vehicle poroperties for vehicle from Divera API.

        Args:
            vehicle_id (int): ID of the vehicle to fetch property data from.
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug(
            "Posting individual vehicle properties for cluster %s", self.ucr_id
        )

        self.permissions.check(PERM_STATUS_VEHICLE)

        part_url = f"{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/set/{vehicle_id}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)

    async def post_using_vehicle_crew(
        self,
        vehicle_id: int,
        mode: str,
        payload: dict[str, str],
    ) -> None:
        """POST add one or more crew to a vehicle.

        Args:
            vehicle_id (int): ID of the vehicle to fetch property data from.
            mode (str): Mode to work with crew members. Can be
                        "add" - adding new crew,
                        "remove" - removing specific crew,
                        "reset" - resetting all crew from vehicle.
            payload (dict): Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If mode is invalid.

        """

        _LOGGER.debug(
            "Posting %s crew members to vehicle %s for cluster %s",
            mode,
            vehicle_id,
            self.ucr_id,
        )

        self.permissions.check(PERM_STATUS_VEHICLE)

        part_url = f"{BASE_API_V2_URL}{API_USING_VEHICLE_CREW}/{mode}/{vehicle_id}"
        if mode in {"add", "remove"}:
            method = "POST"
        elif mode == "reset":
            method = "DELETE"
        else:
            raise HomeAssistantError(
                f"Invalid mode '{mode}' for crew management, can't choose method"
            )

        await self._api_request(part_url, method, payload=payload)

    async def post_news(
        self,
        payload: dict[str, str],
    ) -> None:
        """POST news to Divera.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug(
            "Posting news to unit %s",
            self.ucr_id,
        )

        self.permissions.check(PERM_NEWS)

        part_url = f"{BASE_API_V2_URL}{API_NEWS}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)


class DiveraConfigFlowAPI:
    """API helper methods used by the config flow."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        """Initialize config flow API helper.

        Args:
            session: aiohttp client session.
            base_url: Base URL for the Divera API.

        """
        self._session = session
        self._base_url = base_url

    async def _request_pull_all(self, url: str) -> dict[str, Any]:
        """Async wrapper for get_pull_all to be used in config flow."""
        async with self._session.request(
            method="GET",
            url=url,
            timeout=ClientTimeout(total=10),
        ) as response:
            return await response.json()

    async def _request_auth_login(
        self, url: str, payload: dict[str, str]
    ) -> dict[str, Any]:
        """Async wrapper for auth login to be used in config flow."""
        async with self._session.post(
            url,
            json=payload,
            timeout=ClientTimeout(total=10),
        ) as response:
            return await response.json()

    def _map_to_clusters(
        self, data_pull_all: dict[str, Any], api_key: str
    ) -> dict[str, dict[str, str]]:
        """Format cluster data from config flow validation for easier access."""
        clusters: dict[str, dict[str, str]] = {}
        data_ucr = data_pull_all.get(D_DATA, {}).get(D_UCR, {})

        for ucr, data in data_ucr.items():
            cluster_id = str(data.get(D_CLUSTER_ID, ""))
            clusters[cluster_id] = {
                D_CLUSTER_ID: cluster_id,
                D_CLUSTER_NAME: data.get(D_NAME, ""),
                D_BASE_API_URL: self._base_url,
                D_UPDATE_INTERVAL_DATA: None,  # set later in config flow
                D_UPDATE_INTERVAL_ALARM: None,  # set later in config flow
                D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
                D_RELATIONS_KEY: {
                    ucr: {
                        D_UCR_ID: ucr,
                        D_API_KEY: api_key,
                        D_USERGROUP_ID: data.get(D_USERGROUP_ID, ""),
                    },
                },
            }

        return clusters

    def _format_auth_errors(self, raw_errors: dict | list | str) -> dict[str, str]:
        """Format authentication errors into a standard dictionary."""
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

    async def request_access(
        self,
        user_input: dict[str, Any],
    ) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
        """Validate access and return cluster data.

        Args:
            user_input (dict): User input containing API key or login credentials.

        """

        clusters: dict[str, dict[str, str]] = {}
        validation_errors: dict[str, str] = {}
        api_key: str = ""

        # if no api key but username/password are provided: read api key
        if (
            D_API_KEY not in user_input
            and "username" in user_input
            and "password" in user_input
        ):
            url_auth = f"{self._base_url}{BASE_API_V2_URL}{API_AUTH_LOGIN}"
            payload = {
                "Login": {
                    "username": user_input.get("username", ""),
                    "password": user_input.get("password", ""),
                    "jwt": "false",
                }
            }

            try:
                data_auth = await self._request_auth_login(url_auth, payload)

                if not data_auth.get("success"):
                    return self._format_auth_errors(
                        data_auth.get("errors", {})
                    ), clusters

                data_user = data_auth.get("data", {}).get("user", {})
                api_key = data_user.get("access_token", "")
                # data_ucr = data_auth.get("data", {}).get("ucr", [])

            except (ClientError, TimeoutError) as err:
                _LOGGER.error("Connection error during login validation: %s", err)
                return {"base": "cannot_connect"}, {}
            except (TypeError, AttributeError) as err:
                _LOGGER.error("Data parsing error during login validation: %s", err)
                return {"base": "no_data"}, {}
            except Exception:
                _LOGGER.exception("Unexpected error during login validation")
                return {"base": "unknown"}, {}

        # with api key: read data and create cluster data
        try:
            api_key = user_input.get(D_API_KEY, "") if api_key == "" else api_key
            url_pull_all = f"{self._base_url}{BASE_API_V2_URL}{API_PULL_ALL}?{API_ACCESS_KEY}={api_key}"

            data_pull_all = await self._request_pull_all(url_pull_all)

            if not data_pull_all.get("success"):
                validation_errors["base"] = str(data_pull_all.get("message", {}))
                return validation_errors, clusters

            clusters = self._map_to_clusters(data_pull_all, api_key)

        except ClientError, TimeoutError:
            validation_errors["base"] = "cannot_connect"
        except TypeError, AttributeError:
            validation_errors["base"] = "no_data"
        except Exception:
            validation_errors["base"] = "unknown"

        return validation_errors, clusters
