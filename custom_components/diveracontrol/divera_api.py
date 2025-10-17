"""Communication with Divera 24/7 api."""

import logging
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientError, ClientResponseError, ClientTimeout

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
    API_MESSAGES,
    API_NEWS,
    API_PULL_ALL,
    API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    API_USING_VEHICLE_SET_SINGLE,
    BASE_API_URL,
    BASE_API_V2_URL,
    D_UCR,
    PERM_ALARM,
    PERM_MESSAGES,
    PERM_NEWS,
    PERM_STATUS_VEHICLE,
)
from .utils import permission_check

_LOGGER = logging.getLogger(__name__)


class DiveraAPI:
    """Class to interact with the Divera 24/7 API."""

    def __init__(
        self,
        hass: HomeAssistant,
        ucr_id: str,
        api_key: str,
    ) -> None:
        """Initialize the API client.

        Args:
            hass (HomeAssistant): Instance of HomeAssistant.
            ucr_id (str): user_cluster_relation, the ID to identify the Divera-user.
            api_key (str): API key to access Divera API.

        Returns:
            None

        """
        self.api_key = api_key
        self.ucr_id = ucr_id
        self.hass = hass

        self.session = async_get_clientsession(hass)

    def _redact_url(self, url: str) -> str:
        """Redact API key from URL for logging.

        Args:
            url: URL to redact.

        Returns:
            URL with API key replaced by asterisks.
        """
        return url.replace(self.api_key, "***")

    async def api_request(
        self,
        url: str,
        method: str,
        payload: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Request data from Divera API at the given endpoint.

        Args:
            url (str): URL to request.
            method (str): HTTP method to use. Defaults to "GET".
            perm_key (str): Permission key to check if user is allowed to enter API. Special: All non-restricted APIs have "perm_key=None"
            parameters (dict | None): Dictionary containing URL parameters. Defaults to None.
            payload (dict | None): JSON payload for the request. Defaults to None.

        Returns:
            dict: JSON response from the API.

        """
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

        _LOGGER.debug("API request: %s %s", method, self._redact_url(url))

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
                _LOGGER.debug("API response: %s", self._redact_url(url))
                return data

            # this is needed, as https-response status could be OK, but Divera still returns "success" = false
            if response.json().get("success") is not True:
                raise HomeAssistantError(
                    f"Divera API error: {response.json().get('message')}"
                )

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
            raise HomeAssistantError(f"Failed to connect to Divera API: {err}") from err

    async def close(self) -> None:
        """Cleanup if needed in the future - right now just implemented as a dummy to satisfy linting."""

    async def get_ucr_data(
        self,
    ) -> dict[str, str]:
        """GET all data for user cluster relation from the Divera API. No permission check.

        Args:
            ucr_id (str): user_cluster_relation, the ID to identify the Divera-user.

        Returns:
            dict: JSON response from the API.

        """
        _LOGGER.debug("Fetching all data for cluster %s", self.ucr_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
        method = "GET"
        return await self.api_request(url, method)

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

        permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}"
        method = "POST"

        await self.api_request(url, method, payload=payload)

    async def post_alarms(
        self,
        payload: dict[str, str],
    ) -> None:
        """POST new alarm to Divera API.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug("Posting alarms for unit %s", self.ucr_id)

        permission_check(self.hass, self.ucr_id, PERM_ALARM)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}"
        method = "POST"

        await self.api_request(url, method, payload=payload)

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

        permission_check(self.hass, self.ucr_id, PERM_ALARM)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/{alarm_id}"
        method = "PUT"

        await self.api_request(url, method, payload=payload)

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

        permission_check(self.hass, self.ucr_id, PERM_ALARM)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}"
        method = "POST"

        await self.api_request(url, method, payload=payload)

    async def post_message(
        self,
        payload: dict[str, str],
    ) -> None:
        """POST to close an existing alarm to Divera API.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        """
        _LOGGER.debug("Posting message for cluster %s", self.ucr_id)

        permission_check(self.hass, self.ucr_id, PERM_MESSAGES)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_MESSAGES}"
        method = "POST"

        await self.api_request(url, method, payload=payload)

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

        permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE)

        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}"
        )
        method = "GET"

        return await self.api_request(url, method)

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

        permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE)

        url = (
            f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/set/{vehicle_id}"
        )
        method = "POST"

        await self.api_request(url, method, payload=payload)

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

        permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_CREW}/{mode}/{vehicle_id}"
        if mode in {"add", "remove"}:
            method = "POST"
        elif mode == "reset":
            method = "DELETE"
        else:
            raise HomeAssistantError(
                f"Invalid mode '{mode}' for crew management, can't choose method"
            )

        await self.api_request(url, method, payload=payload)

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

        permission_check(self.hass, self.ucr_id, PERM_NEWS)

        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_NEWS}"
        method = "POST"

        await self.api_request(url, method, payload=payload)
