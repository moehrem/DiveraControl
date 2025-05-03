"""Communication with Divera 24/7 api."""

import logging

from aiohttp import ClientError, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_ACCESS_KEY,
    API_ALARM,
    API_MESSAGES,
    API_PULL_ALL,
    API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    API_USING_VEHICLE_SET_SINGLE,
    BASE_API_URL,
    BASE_API_V2_URL,
    D_UCR,
    PERM_ALARM,
    PERM_MESSAGES,
    PERM_STATUS_VEHICLE,
)
from .utils import log_execution_time, permission_check

LOGGER = logging.getLogger(__name__)


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
                method,
                url,
                json=payload,
                headers=headers,
                timeout=ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    raise ConfigEntryNotReady(
                        f"Divera API error (HTTP status {response.status}) for cluster id '{self.ucr_id}'"
                    )

                if response.status == 200:
                    try:
                        LOGGER.debug("Finished request to Divera API: %s", log_url)
                        return await response.json()
                    except Exception:
                        LOGGER.exception("Error parsing JSON response from Divera API")
                        return await response.json()

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

    async def close(self) -> None:
        """Cleanup if needed in the future - right now just implemented as a dummy to satisfy linting."""

    async def get_ucr_data(
        self,
        ucr_id: str,
    ) -> dict:
        """GET all data for user cluster relation from the Divera API. No permission check.

        Args:
            ucr_id (str): user_cluster_relation, the ID to identify the Divera-user.

        Returns:
            dict: JSON response from the API.

        """
        LOGGER.debug("Fetching all data for cluster %s", self.ucr_id)
        url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_PULL_ALL}"
        method = "GET"
        parameters = {D_UCR: ucr_id}
        return await self.api_request(url, method, parameters=parameters)

    async def post_vehicle_status(
        self,
        vehicle_id: str,
        payload: dict,
    ) -> bool:
        """POST vehicle status and data to Divera API.

        Args:
            vehicle_id (str): Divera-ID of the vehicle to update.
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug("Posting vehicle status and data for cluster %s", self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}"
            method = "POST"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False

    async def post_alarms(
        self,
        payload: dict,
    ) -> bool:
        """POST new alarm to Divera API.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug("Posting alarms for unit %s", self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_ALARM):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}"
            method = "POST"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False

    async def put_alarms(
        self,
        alarm_id: str,
        payload: dict,
    ) -> bool:
        """PUT changes for existing alarm to Divera API.

        Args:
            alarm_id (str): Divera-Alarm-ID which had to be changed.
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug(
            "Putting changes to alarm %s for cluster %s", alarm_id, self.ucr_id
        )

        if permission_check(self.hass, self.ucr_id, PERM_ALARM):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/{alarm_id}"
            method = "PUT"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False

    async def post_close_alarm(
        self,
        payload: dict,
        alarm_id: str,
    ) -> bool:
        """POST to close an existing alarm to Divera API.

        Args:
            alarm_id (str): Divera-Alarm-ID which had to be changed.
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug("Posting to close alarm %s for cluster %s", alarm_id, self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_ALARM):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}"
            method = "POST"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False

    async def post_message(
        self,
        payload: dict,
    ) -> bool:
        """POSt to close an existing alarm to Divera API.

        Args:
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug("Posting message for cluster %s", self.ucr_id)

        if permission_check(self.hass, self.ucr_id, PERM_MESSAGES):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_MESSAGES}"
            method = "POST"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False

    async def get_vehicle_property(
        self,
        vehicle_id: str,
    ) -> dict:
        """GET individual vehicle poroperties for vehicle from Divera API.

        Args:
            vehicle_id (str): ID of the vehicle to fetch property data from.

        Returns:
            dict: JSON response from the API, otherwise empty if no permissions.

        """
        LOGGER.debug(
            "Getting individual vehicle properties for vehicle id %s", vehicle_id
        )

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}"
            method = "GET"
            return await self.api_request(url, method)

        return {}

    async def post_using_vehicle_property(
        self,
        vehicle_id: str,
        payload: dict,
    ) -> bool:
        """POST individual vehicle poroperties for vehicle from Divera API.

        Args:
            vehicle_id (str): ID of the vehicle to fetch property data from.
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug(
            "Posting individual vehicle properties for cluster %s", self.ucr_id
        )

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/set/{vehicle_id}"
            method = "POST"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False

    async def post_using_vehicle_crew(
        self,
        vehicle_id: str,
        mode: str,
        payload: dict,
    ) -> bool:
        """POST add one or more crew to a vehicle.

        Args:
            vehicle_id (str): ID of the vehicle to fetch property data from.
            mode (str): Mode to work with crew members. Can be
                        "add" - adding new crew,
                        "remove" - removing specific crew,
                        "reset" - resetting all crew from vehicle.
            payload (dict): Dictionary of data to send to Divera-API.

        Returns:
            bool: True if API-call successful, False otherwise.

        """
        LOGGER.debug(
            "Posting %s crew members to vehicle %s for cluster %s",
            mode,
            vehicle_id,
            self.ucr_id,
        )

        if permission_check(self.hass, self.ucr_id, PERM_STATUS_VEHICLE):
            url = f"{BASE_API_URL}{BASE_API_V2_URL}{API_USING_VEHICLE_CREW}/{mode}/{vehicle_id}"
            method = "POST"
            # return await self.api_request(url, method, payload=payload)
            await self.api_request(url, method, payload=payload)
            return True

        return False
