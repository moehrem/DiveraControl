"""Funktion: Kommunikation mit der Divera 24/7 API.

Verantwortung:

    Bereitstellen von Klassen und Methoden für die direkte Interaktion mit der API (z. B. Authentifizierung, Abrufen von Daten).
    Verarbeitung und Rückgabe der rohen API-Daten.
    Abstraktion der API-Details (z. B. HTTP-Requests, Header, etc.).

Kommunikation:

    Wird vom coordinator.py verwendet.
    Gibt die Ergebnisse (z. B. JSON oder strukturierte Python-Daten) zurück
"""

import logging
from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    D_COORDINATOR,
    DOMAIN,
    API_ACCESS_KEY,
    # API_ACCESS_KEY,
    API_ALARM,
    API_AUTH_LOGIN,
    # API_EVENT,
    API_MESSAGES,
    # API_MESSAGE_CHANNEL,
    # API_NEWS,
    # API_OPERATIONS,
    API_PULL_ALL,
    # API_PULL_VEHICLE,
    API_USING_VEHICLE_SET_SINGLE,
    # API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    BASE_API_URL,
    BASE_API_V2_URL,
    API_STATUSGEBER,
    API_STATUSGEBER_SIMPLE,
    # permissions
    PERM_MESSAGES,
    PERM_ALARM,
    PERM_NEWS,
    PERM_EVENT,
    PERM_MESSAGE_CHANNEL,
    PERM_REPORT,
    PERM_STATUS,
    PERM_STATUS_MANUAL,
    PERM_STATUS_PLANER,
    PERM_STATUS_GEOFENCE,
    PERM_STATUS_VEHICLE,
    PERM_MONITOR,
    PERM_MONITOR_SHOW_NAMES,
    PERM_PERSONNEL_PHONENUMBERS,
    PERM_LOCALMANAGEMENT,
    PERM_MANAGEMENT,
    PERM_DASHBOARD,
    PERM_CROSS_UNIT,
    PERM_LOCALMONITOR,
    PERM_LOCALMONITOR_SHOW_NAMES,
    PERM_FMS_EDITOR,
)

_LOGGER = logging.getLogger(__name__)


class DiveraAPI:
    """Class to interact with the Divera 24/7 API."""

    def __init__(self, hass: HomeAssistant, api_key: str, ucr: str) -> None:
        """Initialize the API client."""
        self.api_key = api_key
        self.ucr = ucr
        # self.data = hass.data[DOMAIN][str(ucr)][D_COORDINATOR].data
        self.hass = hass

        self.session = async_get_clientsession(hass)

    async def api_request(
        self,
        url: str,
        method: str,
        perm_key: str,
        parameters: dict | None = {},
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

        # permission check
        # if perm_key is not None:
        #     if not permission_request(self.hass, self.ucr, perm_key):
        #         return None

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

        # create URL for logging
        log_url = url.replace(self.api_key, "**********")

        try:
            async with self.session.request(
                method, url, json=payload, headers=headers, timeout=10
            ) as response:
                if response.status == 200:
                    try:
                        return await response.json()
                    except Exception:
                        return response

                _LOGGER.error(
                    "Error in %s request for hub id '%s'. Status: '%s', reason: '%s', url: '%s'",
                    method,
                    self.ucr,
                    response.status,
                    response.reason,
                    log_url,
                )

                return {}
        except ClientError as e:
            _LOGGER.error(
                "client error: %s for hub id %s from url %s", e, self.ucr, log_url
            )
            return {}

    # async def get_master_data(self) -> dict:
    #     """GET all data based on current users authorizations from the Divera API."""
    #     _LOGGER.debug("Fetching master data")
    #     url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
    #     method = "GET"
    #     perm_key = None
    #     return await self.api_request(url, perm_key, method)

    async def get_ucr_data(self) -> dict:
        """GET all data for user cluster relation from the Divera API."""
        _LOGGER.debug("Fetching all data for HUB %s", self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
        method = "GET"
        params = {"ucr": self.ucr}
        perm_key = None
        return await self.api_request(url, method, perm_key, parameters=params)

    async def post_user_status_advanced(self, payload) -> dict:
        """POST userstatus to Divera API."""
        _LOGGER.debug("Posting user status for HUB %s", self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_STATUSGEBER}"
        method = "POST"
        perm_key = PERM_STATUS
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_user_status_simple(self, params) -> dict:
        """POST userstatus to Divera API."""
        _LOGGER.debug("Posting user status for HUB %s", self.ucr)
        url = f"{BASE_API_URL}{API_STATUSGEBER_SIMPLE}"
        method = "POST"
        perm_key = PERM_STATUS
        return await self.api_request(url, method, perm_key, parameters=params)

    async def post_vehicle_status(self, vehicle_id, payload) -> dict:
        """POST vehicle status and data to Divera API."""
        _LOGGER.debug("Posting vehicle status and data for HUB %s", self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}"
        method = "POST"
        perm_key = PERM_STATUS_VEHICLE
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_alarms(self, payload) -> dict:
        """POST new alarm to Divera API."""
        _LOGGER.debug("Posting alarms for HUB %s", self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}"
        method = "POST"
        perm_key = PERM_ALARM
        return await self.api_request(url, method, perm_key, payload=payload)

    async def put_alarms(self, payload, alarm_id) -> dict:
        """PUT changes for existing alarm to Divera API."""
        _LOGGER.debug("Putting changes to alarm %s for HUB %s", alarm_id, self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/{alarm_id}"
        method = "PUT"
        perm_key = PERM_ALARM
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_close_alarm(self, payload, alarm_id) -> dict:
        """POSt to close an existing alarm to Divera API."""
        _LOGGER.debug("Posting to close alarm %s for HUB %s", alarm_id, self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}"
        method = "POST"
        perm_key = PERM_ALARM
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_message(self, payload) -> dict:
        """POSt to close an existing alarm to Divera API."""
        _LOGGER.debug("Posting message for HUB %s", self.ucr)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_MESSAGES}"
        method = "POST"
        perm_key = PERM_MESSAGES
        return await self.api_request(url, method, perm_key, payload=payload)

    async def get_vehicle_property(self, vehicle_id) -> dict:
        """GET individual vehicle poroperties for vehicle from Divera API."""
        _LOGGER.debug("Getting individual vehicle properties for HUB %s", self.ucr)
        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}"
        )
        method = "GET"
        perm_key = PERM_STATUS_VEHICLE
        return await self.api_request(url, method, perm_key)

    async def post_using_vehicle_property(self, payload, vehicle_id) -> dict:
        """POST individual vehicle poroperties for vehicle from Divera API."""
        _LOGGER.debug("Posting individual vehicle properties for HUB %s", self.ucr)
        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/set/{vehicle_id}"
        )
        method = "POST"
        perm_key = PERM_STATUS_VEHICLE
        return await self.api_request(url, method, perm_key, payload=payload)


class DiveraCredentials:
    """Validates Divera credentials: username, password, api-key."""

    @staticmethod
    async def validate_login(
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
            hubs (dict): Mapping of hub IDs to their names.
            api_key (str): Retrieved API key.

        """
        errors = {}  # init errors, as with multiple hubs errors of other hubs might still be set
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_AUTH_LOGIN}"
        payload = {
            "Login": {
                "username": user_input.get("username", ""),
                "password": user_input.get("password", ""),
                "jwt": "false",
            }
        }

        hubs = {}
        api_key = ""

        try:
            async with session.post(url, json=payload, timeout=10) as response:
                data = await response.json()

                if not data.get("success"):
                    raw_errors = data.get("errors", {})
                    formatted_errors = {}

                    if isinstance(raw_errors, list):
                        formatted_errors["base"] = "; ".join(raw_errors)
                    elif isinstance(raw_errors, dict):
                        for value in raw_errors.values():
                            if isinstance(value, list):
                                formatted_errors["base"] = "; ".join(value)
                            else:
                                formatted_errors["base"] = str(value)
                    else:
                        formatted_errors["base"] = str(raw_errors)

                    return formatted_errors, hubs, api_key

                user_data = data.get("data", {}).get("user", {})
                api_key = user_data.get("access_token", "")

                hubs = (
                    {
                        str(ucr["id"]): ucr.get("name", f"Hub_{ucr['id']}")
                        for ucr in data.get("data", {}).get("ucr", [])
                    }
                    if "ucr" in data.get("data", {})
                    else {}
                )

        except (ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except (TypeError, AttributeError):
            errors["base"] = "no_data"
        except Exception:
            errors["base"] = "unknown"

        return errors, hubs, api_key

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
            hubs (dict): Mapping of hub IDs to their names.
            api_key (str): Retrieved API key.

        """
        hubs = {}
        errors = {}  # init errors, as with multiple hubs errors of other hubs might still be set
        api_key = user_input.get("api_key", "")
        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}?{API_ACCESS_KEY}={api_key}"
        )

        try:
            async with session.get(url, timeout=10) as response:
                data = await response.json()

                if response.status not in [200, 201]:
                    errors["base"] = data.get("message", {})
                    return errors, hubs, api_key

                ucr_data = data.get("data", {}).get("ucr", {})
                hubs = {key: value["name"] for key, value in ucr_data.items()}

        except (ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except (TypeError, AttributeError):
            errors["base"] = "no_data"
        except Exception:
            errors["base"] = "unknown"

        return errors, hubs, api_key
