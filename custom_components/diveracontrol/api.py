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

from .utils import log_execution_time
from .const import (
    D_COORDINATOR,
    DOMAIN,
    D_DATA,
    D_UCR,
    D_UCR_ID,
    D_USER,
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

LOGGER = logging.getLogger(__name__)


class DiveraAPI:
    """Class to interact with the Divera 24/7 API."""

    def __init__(self, hass: HomeAssistant, cluster_id: str) -> None:
        """Initialize the API client."""
        self.api_key = None
        self.cluster_id = cluster_id
        self.hass = hass

        self.session = async_get_clientsession(hass)

    def set_api_key(self, api_key: str):
        """Sets api-key dynamically based on device(user)."""
        self.api_key = api_key

    @log_execution_time
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
        #     if not permission_request(self.hass, self.cluster_id, perm_key):
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

                LOGGER.error(
                    "Error in %s request for cluster id '%s'. Status: '%s', reason: '%s', url: '%s'",
                    method,
                    self.cluster_id,
                    response.status,
                    response.reason,
                    log_url,
                )

                return {}
        except ClientError as e:
            LOGGER.error(
                "client error: %s for cluster id %s from url %s",
                e,
                self.cluster_id,
                log_url,
            )
            return {}

    async def get_ucr_data(self, ucr_id) -> dict:
        """GET all data for user cluster relation from the Divera API."""
        LOGGER.debug("Fetching all data for cluster %s", self.cluster_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
        method = "GET"
        params = {"ucr": ucr_id}
        perm_key = None
        return await self.api_request(url, method, perm_key, parameters=params)

    async def post_user_status_advanced(self, payload) -> dict:
        """POST userstatus to Divera API."""
        LOGGER.debug("Posting user status for cluster %s", self.cluster_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_STATUSGEBER}"
        method = "POST"
        perm_key = PERM_STATUS
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_user_status_simple(self, params) -> dict:
        """POST userstatus to Divera API."""
        LOGGER.debug("Posting user status for cluster %s", self.cluster_id)
        url = f"{BASE_API_URL}{API_STATUSGEBER_SIMPLE}"
        method = "POST"
        perm_key = PERM_STATUS
        return await self.api_request(url, method, perm_key, parameters=params)

    async def post_vehicle_status(self, vehicle_id, payload) -> dict:
        """POST vehicle status and data to Divera API."""
        LOGGER.debug("Posting vehicle status and data for cluster %s", self.cluster_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}"
        method = "POST"
        perm_key = PERM_STATUS_VEHICLE
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_alarms(self, payload) -> dict:
        """POST new alarm to Divera API."""
        LOGGER.debug("Posting alarms for unit %s", self.cluster_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}"
        method = "POST"
        perm_key = PERM_ALARM
        return await self.api_request(url, method, perm_key, payload=payload)

    async def put_alarms(self, payload, alarm_id) -> dict:
        """PUT changes for existing alarm to Divera API."""
        LOGGER.debug(
            "Putting changes to alarm %s for cluster %s", alarm_id, self.cluster_id
        )
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/{alarm_id}"
        method = "PUT"
        perm_key = PERM_ALARM
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_close_alarm(self, payload, alarm_id) -> dict:
        """POSt to close an existing alarm to Divera API."""
        LOGGER.debug(
            "Posting to close alarm %s for cluster %s", alarm_id, self.cluster_id
        )
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}"
        method = "POST"
        perm_key = PERM_ALARM
        return await self.api_request(url, method, perm_key, payload=payload)

    async def post_message(self, payload) -> dict:
        """POSt to close an existing alarm to Divera API."""
        LOGGER.debug("Posting message for cluster %s", self.cluster_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_MESSAGES}"
        method = "POST"
        perm_key = PERM_MESSAGES
        return await self.api_request(url, method, perm_key, payload=payload)

    async def get_vehicle_property(self, vehicle_id) -> dict:
        """GET individual vehicle poroperties for vehicle from Divera API."""
        LOGGER.debug(
            "Getting individual vehicle properties for vehicle id %s", vehicle_id
        )
        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}"
        )
        method = "GET"
        perm_key = PERM_STATUS_VEHICLE
        return await self.api_request(url, method, perm_key)

    async def post_using_vehicle_property(self, payload, vehicle_id) -> dict:
        """POST individual vehicle poroperties for vehicle from Divera API."""
        LOGGER.debug(
            "Posting individual vehicle properties for cluster %s", self.cluster_id
        )
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
        """Validate API access and fetch all instance names."""

        errors = {}  # Fehler zurücksetzen
        url_auth = f"{BASE_API_URL}{BASE_API_V2_URL}{API_AUTH_LOGIN}"
        payload = {
            "Login": {
                "username": user_input.get("username", ""),
                "password": user_input.get("password", ""),
                "jwt": "false",
            }
        }

        clusters = {}
        api_key = ""

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

                data_ucr = data_auth.get("data", {}).get("ucr", {})
                data_user = data_auth.get("data", {}).get("user", {})
                api_key = data_user.get("access_token", "")

                clusters = (
                    {
                        str(ucr["id"]): ucr.get("name", f"Hub_{ucr['id']}")
                        for ucr in data_auth.get("data", {}).get("ucr", [])
                    }
                    if "ucr" in data_auth.get("data", {})
                    else {}
                )

        except (ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except (TypeError, AttributeError):
            errors["base"] = "no_data"
        except Exception:
            errors["base"] = "unknown"

        # Cluster-Daten abrufen
        raw_url_ucr = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
        clusters = {}

        for item in data_ucr:
            ucr = str(item.get("id"))  # ID der UCR als String
            if ucr:
                url_ucr = f"{raw_url_ucr}?accesskey={api_key}&ucr={ucr}"
                try:
                    async with session.get(url_ucr, timeout=10) as response:
                        data_ucr_response = await response.json()

                        if not data_ucr_response.get(
                            "success"
                        ) or response.status not in [
                            200,
                            201,
                        ]:
                            errors["base"] = data_ucr_response.get("message", {})
                            return errors, clusters

                    data_ucr_data = data_ucr_response.get(D_DATA, {}).get(D_UCR, {})
                    data_user = data_ucr_response.get(D_DATA, {}).get(D_USER, {})

                    cluster_id = str(data_ucr_data.get(ucr, {}).get("cluster_id", ""))
                    cluster_name = data_ucr_data.get(ucr, {}).get("name", "")
                    user_name = f"{data_user.get('firstname', '')} {data_user.get('lastname', '')}".strip()

                    # 1. Falls `cluster_id` noch nicht existiert, initialisiere es mit einem Dictionary, das `ucr_name` speichert
                    if cluster_id not in clusters:
                        clusters[cluster_id] = {
                            "cluster_name": cluster_name,
                            "user_cluster_relations": {},
                        }

                    # 2. Falls `ucr` unter `cluster_id` nicht existiert, füge es hinzu
                    if ucr not in clusters[cluster_id]["user_cluster_relations"]:
                        clusters[cluster_id]["user_cluster_relations"][ucr] = {
                            "user_name": user_name,
                            "api_key": api_key,
                        }

                except (ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                except (TypeError, AttributeError):
                    errors["base"] = "no_data"
                except Exception:
                    errors["base"] = "unknown"

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
                    return errors, clusters, api_key

                ucr_data = data.get("data", {}).get("ucr", {})
                clusters = {key: value["name"] for key, value in ucr_data.items()}

        except (ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except (TypeError, AttributeError):
            errors["base"] = "no_data"
        except Exception:
            errors["base"] = "unknown"

        return errors, clusters, api_key
