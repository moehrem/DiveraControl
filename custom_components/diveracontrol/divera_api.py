"""Communication with Divera 24/7 API.

This module provides a Python client for interacting with the Divera 24/7 API.

The module implements:
- Base API client with shared request handling and error management
- Config flow helpers for cluster discovery and validation
- Runtime API operations with permission checking
- Comprehensive type hints and validation
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any, Literal, TypedDict
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
    API_AUTH_LOGIN,
    API_MESSAGES,
    API_NEWS,
    API_PULL_ALL,
    API_USER_STATUS,
    API_USING_VEHICLE_CREW,
    API_USING_VEHICLE_PROP,
    API_USING_VEHICLE_SET_SINGLE,
    BASE_API_URL,
    BASE_API_V2_URL,
    D_ACCESSKEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_DATA,
    D_NAME,
    D_RELATIONS_KEY,
    D_UCR,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
    D_USERNAME,
    PERM_ALARM,
    PERM_MESSAGES,
    PERM_NEWS,
    PERM_STATUS_USER,
    PERM_STATUS_VEHICLE,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
)
from .divera_permissions import DiveraPermissions

_LOGGER = logging.getLogger(__name__)


# ========== Type Definitions ==========


class DiveraAPIResponse(TypedDict, total=False):
    """TypedDict for Divera API responses."""

    success: bool
    message: str
    data: dict[str, Any]


class ClusterEntry(TypedDict):
    """TypedDict for a cluster entry in config flow."""

    cluster_id: str
    cluster_name: str | None
    base_api_url: str
    update_interval_data: int
    update_interval_alarm: int
    user_cluster_relations: dict[str, dict[str, str]]


class AuthPayload(TypedDict):
    """TypedDict for authentication login payload."""

    Login: dict[str, str]


class ConfigFlowErrorCode(str, Enum):
    """Enum for config flow error codes."""

    INVALID_CREDENTIALS = "invalid_credentials"
    CANNOT_CONNECT = "cannot_connect"
    NO_DATA = "no_data"
    UNKNOWN = "unknown"
    NO_CLUSTERS_FOUND = "no_clusters_found"
    INVALID_CLUSTER_STRUCTURE = "invalid_cluster_structure"
    MISSING_CLUSTER_FIELDS = "missing_cluster_fields"
    INVALID_RELATION_STRUCTURE = "invalid_relation_structure"
    MISSING_RELATION_FIELDS = "missing_relation_fields"
    INVALID_ACCESSKEY_TYPE = "invalid_accesskey_type"
    INVALID_USERNAME_TYPE = "invalid_username_type"
    EMPTY_RELATIONS = "empty_relations"


# ========== Base API Client ==========


class DiveraAPIClient:
    """Base class for Divera API clients with shared functionality.

    This class provides core API request handling, error management, and
    URL construction utilities. It can be used directly for config flow
    operations or as a base class for runtime API operations.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 5,
    ) -> None:
        """Initialize the base API client.

        Args:
            hass: Home Assistant instance.
            base_url: Base URL for the Divera API.
            timeout: Request timeout in seconds. Defaults to 10.
            max_retries: Maximum number of retries for failed requests. Defaults to 5.
        """
        self._session = async_get_clientsession(hass)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

    def _build_url(self, endpoint: str, params: dict[str, str] | None = None) -> str:
        """Build a complete URL from base URL, endpoint, and parameters.

        Args:
            endpoint: API endpoint path.
            params: Query parameters for the URL.

        Returns:
            Complete URL with query parameters.
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return url

    def _redact_url(self, url: str, sensitive_keys: set[str] | None = None) -> str:
        """Redact sensitive data from URL for safe logging.

        Args:
            url: URL to redact.
            sensitive_keys: Set of parameter names to redact. Defaults to API_ACCESS_KEY.

        Returns:
            URL with sensitive data replaced by asterisks.
        """
        if sensitive_keys is None:
            sensitive_keys = {API_ACCESS_KEY, D_ACCESSKEY, "password"}

        if not url:
            return url

        from urllib.parse import parse_qs, urlparse, urlunparse

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        for key in sensitive_keys:
            if key in query_params:
                query_params[key] = ["***"]

        redacted_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=redacted_query))

    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float | None = None,
        retry_count: int = 0,
    ) -> DiveraAPIResponse:
        """Make a request to the Divera API with retry logic.

        Args:
            endpoint: API endpoint path.
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            params: Query parameters for the request.
            payload: Data to send with the request (for POST/PUT).
            timeout: Request timeout in seconds. Uses instance timeout if None.
            retry_count: Current retry attempt number.

        Returns:
            DiveraAPIResponse: JSON response from the API.

        Raises:
            ConfigEntryAuthFailed: If authentication fails (HTTP 401/403).
            ConfigEntryNotReady: If the API is unavailable (HTTP 5xx or timeout).
            HomeAssistantError: For other API errors.
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        url = self._build_url(endpoint, params)

        # Identify sensitive keys for URL redaction
        sensitive_keys = {API_ACCESS_KEY, D_ACCESSKEY}
        if params:
            sensitive_keys.update(
                k for k in params if "key" in k.lower() or "password" in k.lower()
            )

        _LOGGER.debug(
            "API request [attempt %d]: %s %s",
            retry_count + 1,
            method,
            self._redact_url(url, sensitive_keys),
            extra={"endpoint": endpoint},
        )

        try:
            async with self._session.request(
                method,
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "HomeAssistant-DiveraControl",
                },
                timeout=ClientTimeout(total=effective_timeout),
            ) as response:
                response_data = await response.json()

                # Check for Divera-specific success flag
                # IMPORTANT: Divera API may return HTTP 200 even for application-level errors, so we must check the 'success' field in the response
                if response.status == 200 and response_data.get("success") is not True:
                    raise HomeAssistantError(
                        f"Divera API error: {response_data.get('message', 'Unknown error')}"
                    )

                response.raise_for_status()
                return response_data

        except ClientResponseError as err:
            # Retry on server errors (5xx) and rate limiting (429)
            if err.status >= 500 and retry_count < self._max_retries:
                _LOGGER.warning(
                    "Divera API server error (HTTP %d), retrying... (%d/%d)",
                    err.status,
                    retry_count + 1,
                    self._max_retries,
                )
                await asyncio.sleep(1 * (retry_count + 1))  # Exponential backoff
                return await self._request(
                    endpoint,
                    method,
                    params,
                    payload,
                    timeout,
                    retry_count + 1,
                )

            if err.status in [401, 403]:
                raise ConfigEntryAuthFailed(
                    f"Invalid credentials (HTTP {err.status})"
                ) from err
            if err.status >= 500:
                raise ConfigEntryNotReady(
                    f"Divera API unavailable (HTTP {err.status})"
                ) from err
            raise HomeAssistantError(
                f"Divera API error (HTTP {err.status}): {err.message}"
            ) from err

        except TimeoutError as err:
            if retry_count < self._max_retries:
                _LOGGER.warning(
                    "Divera API timeout, retrying... (%d/%d)",
                    retry_count + 1,
                    self._max_retries,
                )
                return await self._request(
                    endpoint,
                    method,
                    params,
                    payload,
                    timeout,
                    retry_count + 1,
                )
            raise ConfigEntryNotReady("Timeout connecting to Divera API") from err

        except ClientError as err:
            request_url = getattr(getattr(err, "request_info", None), "real_url", None)
            url_for_log = (
                self._redact_url(str(request_url), sensitive_keys)
                if request_url
                else "unknown"
            )
            raise HomeAssistantError(
                f"Failed to connect to Divera API at URL: {url_for_log}"
            ) from err

    # ========== Config Flow Helper Methods ==========

    async def _request_pull_all(self, accesskey: str) -> dict[str, Any]:
        """Request pull_all data from Divera API for config flow.

        Args:
            accesskey: API access key for authentication.

        Returns:
            dict: JSON response from the API.
        """
        params = {API_ACCESS_KEY: accesskey}
        _LOGGER.debug("Requesting pull_all data from Divera API")
        return await self._request(
            f"{BASE_API_V2_URL}{API_PULL_ALL}",
            "GET",
            params=params,
        )

    async def _request_auth_login(self, username: str, password: str) -> dict[str, Any]:
        """Request authentication login from Divera API for config flow.

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
            dict: JSON response from the API.
        """
        payload: AuthPayload = {
            "Login": {
                "username": username,
                "password": password,
                "jwt": "false",
            }
        }
        _LOGGER.debug("Requesting auth login from Divera API")
        return await self._request(
            f"{BASE_API_V2_URL}{API_AUTH_LOGIN}",
            "POST",
            payload=payload,
        )

    def _map_to_clusters(
        self,
        data_pull_all: dict[str, Any],
        accesskey: str,
        base_api_url: str,
        update_interval_data: int,
        update_interval_alarm: int,
    ) -> dict[str, ClusterEntry]:
        """Format cluster data from pull_all response for easier access.

        Args:
            data_pull_all: Response data from pull_all API call.
            accesskey: API access key used for authentication.
            base_api_url: Base API URL to use for clusters.
            update_interval_data: Data update interval for clusters.
            update_interval_alarm: Alarm update interval for clusters.

        Returns:
            dict: Formatted cluster data with all required fields.
        """
        clusters: dict[str, ClusterEntry] = {}

        data_ucr = data_pull_all.get(D_DATA, {}).get(D_UCR, {})
        data_user = data_pull_all.get(D_DATA, {}).get(D_USER, {})
        user_name = (
            f"{data_user.get('firstname', '')} {data_user.get('lastname', '')}".strip()
        )

        for ucr, data in data_ucr.items():
            cluster_id = str(data.get(D_CLUSTER_ID, ""))
            if not cluster_id:
                continue

            clusters[cluster_id] = {
                "cluster_id": cluster_id,
                "cluster_name": data.get(D_NAME),
                "base_api_url": base_api_url,
                "update_interval_data": update_interval_data,
                "update_interval_alarm": update_interval_alarm,
                "user_cluster_relations": {
                    ucr: {
                        D_USERNAME: user_name,
                        D_ACCESSKEY: accesskey,
                    },
                },
            }

        return clusters

    def _format_auth_errors(self, raw_errors: dict | list | str) -> dict[str, str]:
        """Format authentication errors into a standard dictionary.

        Args:
            raw_errors: Raw error data from API response.

        Returns:
            dict: Formatted error dictionary with 'base' key.
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

    def _validate_relation_entry(
        self,
        ucr_id: str,
        relation: dict[str, Any],
        cluster_id: str,
    ) -> ConfigFlowErrorCode | None:
        """Validate a single relation entry.

        Args:
            ucr_id: User cluster relation ID.
            relation: Relation data to validate.
            cluster_id: Parent cluster ID.

        Returns:
            ConfigFlowErrorCode if validation fails, None otherwise.
        """
        required_keys = {D_ACCESSKEY, D_USERNAME}

        if not isinstance(relation, dict):
            return ConfigFlowErrorCode.INVALID_RELATION_STRUCTURE

        missing_relation_keys = required_keys - relation.keys()
        if missing_relation_keys:
            return ConfigFlowErrorCode.MISSING_RELATION_FIELDS

        if not isinstance(relation.get(D_ACCESSKEY), str):
            return ConfigFlowErrorCode.INVALID_ACCESSKEY_TYPE
        if not isinstance(relation.get(D_USERNAME), str):
            return ConfigFlowErrorCode.INVALID_USERNAME_TYPE

        return None

    def _validate_cluster_entry(
        self,
        cluster_id: str,
        entry: dict[str, Any],
    ) -> ConfigFlowErrorCode | None:
        """Validate a single cluster entry.

        Args:
            cluster_id: Cluster ID to validate.
            entry: Cluster data to validate.

        Returns:
            ConfigFlowErrorCode if validation fails, None otherwise.
        """
        required_keys = {
            D_CLUSTER_ID,
            D_CLUSTER_NAME,
            D_RELATIONS_KEY,
            D_BASE_API_URL,
            D_UPDATE_INTERVAL_ALARM,
            D_UPDATE_INTERVAL_DATA,
        }

        if not isinstance(entry, dict):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE

        missing_cluster_keys = required_keys - entry.keys()
        if missing_cluster_keys:
            return ConfigFlowErrorCode.MISSING_CLUSTER_FIELDS

        # Validate cluster field types
        if not isinstance(entry.get(D_CLUSTER_ID), str):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE
        if not isinstance(entry.get(D_CLUSTER_NAME), str):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE
        if not isinstance(entry.get(D_BASE_API_URL), str):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE
        if not isinstance(entry.get(D_UPDATE_INTERVAL_ALARM), int):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE
        if not isinstance(entry.get(D_UPDATE_INTERVAL_DATA), int):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE

        # Validate relations
        relations = entry.get(D_RELATIONS_KEY, {})
        if not isinstance(relations, dict):
            return ConfigFlowErrorCode.INVALID_CLUSTER_STRUCTURE
        if not relations:
            return ConfigFlowErrorCode.EMPTY_RELATIONS

        for ucr_id, relation in relations.items():
            relation_error = self._validate_relation_entry(ucr_id, relation, cluster_id)
            if relation_error:
                return relation_error

        return None

    def _validate_entries_structure(
        self,
        entries: dict[str, dict[str, Any]],
    ) -> tuple[bool, dict[str, str]]:
        """Validate that all cluster entries have the required structure.

        Args:
            entries: Dictionary of cluster entries to validate.

        Returns:
            Tuple of (is_valid, errors) where errors contains specific error messages.
        """
        if not entries:
            return False, {"base": ConfigFlowErrorCode.NO_CLUSTERS_FOUND.value}

        for cluster_id, entry in entries.items():
            error_code = self._validate_cluster_entry(cluster_id, entry)
            if error_code:
                return False, {"base": error_code.value}

        return True, {}

    async def _get_accesskey_from_login(
        self,
        username: str,
        password: str,
    ) -> str:
        """Get access key from username/password login.

        Args:
            username: Username for login.
            password: Password for login.

        Returns:
            str: Access key if login successful, empty string otherwise.
        """
        try:
            data_auth = await self._request_auth_login(username, password)

            if not data_auth.get("success", False):
                _LOGGER.debug(
                    "Login failed: %s", data_auth.get("message", "Unknown error")
                )
                return ""

            access_token = (
                data_auth.get("data", {}).get("user", {}).get("access_token", "")
            )
            if not access_token:
                _LOGGER.debug("No access token in response")
                return ""

            return access_token

        except (ClientError, TimeoutError, ConfigEntryAuthFailed) as err:
            _LOGGER.error("Connection error during login validation: %s", err)
            return ""
        except Exception as ex:
            _LOGGER.exception("Unexpected error during login validation: %s", ex)
            return ""

    async def _fetch_and_validate_clusters(
        self,
        accesskey: str,
        base_api_url: str,
        update_interval_data: int,
        update_interval_alarm: int,
    ) -> tuple[dict[str, str], dict[str, ClusterEntry]]:
        """Fetch cluster data from API and validate it.

        Args:
            accesskey: API access key for authentication.
            base_api_url: Base API URL to use.
            update_interval_data: Data update interval.
            update_interval_alarm: Alarm update interval.

        Returns:
            Tuple of (errors, clusters) where errors contains validation errors
            and clusters contains the validated cluster data.
        """
        clusters: dict[str, ClusterEntry] = {}
        validation_errors: dict[str, str] = {}

        try:
            data_pull_all = await self._request_pull_all(accesskey)

            if not data_pull_all.get("success", False):
                validation_errors["base"] = str(
                    data_pull_all.get("message", "Unknown error")
                )
                return validation_errors, clusters

            clusters = self._map_to_clusters(
                data_pull_all,
                accesskey,
                base_api_url,
                update_interval_data,
                update_interval_alarm,
            )

            # Validate clusters
            is_valid, entry_errors = self._validate_entries_structure(clusters)
            if not is_valid:
                return entry_errors, {}

        except (ClientError, TimeoutError, ConfigEntryAuthFailed):
            validation_errors["base"] = ConfigFlowErrorCode.CANNOT_CONNECT.value
        except (TypeError, AttributeError):
            validation_errors["base"] = ConfigFlowErrorCode.NO_DATA.value
        except Exception as ex:
            _LOGGER.exception(
                "Unexpected error in _fetch_and_validate_clusters: %s", ex
            )
            validation_errors["base"] = ConfigFlowErrorCode.UNKNOWN.value

        return validation_errors, clusters

    async def request_access(
        self,
        user_input: dict[str, Any],
    ) -> tuple[dict[str, str], dict[str, ClusterEntry]]:
        """Validate access and return cluster data for config flow.

        This is the main method used by the config flow to validate user input
        and retrieve available clusters.

        Args:
            user_input: User input containing API key or login credentials.
                Expected keys:
                - accesskey: API access key (optional)
                - username: Username for login (optional)
                - password: Password for login (optional)
                - base_api_url: Base API URL (optional)
                - update_interval_data: Data update interval (optional)
                - update_interval_alarm: Alarm update interval (optional)

        Returns:
            Tuple of (errors, clusters) where errors contains validation errors
            and clusters contains the validated cluster data.
        """
        clusters: dict[str, ClusterEntry] = {}
        validation_errors: dict[str, str] = {}
        accesskey: str = ""

        # Extract configuration
        base_api_url = user_input.get(D_BASE_API_URL, BASE_API_URL)
        update_interval_data = user_input.get(
            D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
        )
        update_interval_alarm = user_input.get(
            D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
        )

        # Step 1: Get accesskey (either from input or via login)
        if D_ACCESSKEY in user_input:
            accesskey = str(user_input[D_ACCESSKEY]).strip()
        elif "username" in user_input and "password" in user_input:
            username = str(user_input["username"]).strip()
            password = str(user_input["password"]).strip()
            accesskey = await self._get_accesskey_from_login(username, password)
            if not accesskey:
                return {"base": ConfigFlowErrorCode.INVALID_CREDENTIALS.value}, clusters

        if not accesskey:
            return {"base": ConfigFlowErrorCode.INVALID_CREDENTIALS.value}, clusters

        # Step 2: Fetch and validate clusters
        validation_errors, clusters = await self._fetch_and_validate_clusters(
            accesskey,
            base_api_url,
            update_interval_data,
            update_interval_alarm,
        )

        return validation_errors, clusters


# ========== Runtime API Client ==========


class DiveraAPI(DiveraAPIClient):
    """Class to interact with the Divera 24/7 API for runtime operations.

    This class extends DiveraAPIClient with fixed ucr_id and accesskey,
    automatically including them in all API requests. It provides methods
    for all supported Divera API operations with permission checking.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        ucr_id: str,
        accesskey: str,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 5,
    ) -> None:
        """Initialize the API client.

        Args:
            hass: Home Assistant instance.
            ucr_id: user_cluster_relation, the ID to identify the Divera-user.
            accesskey: API key to access Divera API.
            base_url: Base URL for the Divera API.
            timeout: Request timeout in seconds. Defaults to 10.
            max_retries: Maximum number of retries for failed requests. Defaults to 5.
        """
        super().__init__(hass, base_url, timeout, max_retries)
        self.ucr_id = ucr_id
        self.accesskey = accesskey
        self.permissions = DiveraPermissions()
        self.permissions.ucr_id = ucr_id

    def _get_default_params(self) -> dict[str, str]:
        """Get default parameters for all API requests.

        Returns:
            dict: Default parameters including accesskey and ucr_id.
        """
        return {
            API_ACCESS_KEY: self.accesskey,
            D_UCR: self.ucr_id,
        }

    async def _api_request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        additional_params: dict[str, str] | None = None,
    ) -> DiveraAPIResponse:
        """Request data from Divera API at the given endpoint.

        Automatically includes ucr_id and accesskey in the request parameters.

        Args:
            endpoint: API endpoint path (relative to base URL).
            method: HTTP method to use for the request.
            payload: Data to send with the request.
            additional_params: Additional query parameters.

        Returns:
            DiveraAPIResponse: JSON response from the API.
        """
        params = {**self._get_default_params()}
        if additional_params:
            params.update(additional_params)

        return await self._request(endpoint, method, params=params, payload=payload)

    async def get_pull_all(self) -> DiveraAPIResponse:
        """GET all data for user cluster relation from the Divera API.

        No permission check is performed for this endpoint.
        Updates permissions from the response data.

        Returns:
            DiveraAPIResponse: JSON response from the API.
        """
        _LOGGER.debug("Fetching all data for cluster %s", self.ucr_id)
        data = await self._api_request(f"{BASE_API_V2_URL}{API_PULL_ALL}", "GET")

        if data.get("success", False):
            self.permissions.replace_permissions_from_ucr_data(data)

        return DiveraAPIResponse(data)

    # ========== Alarm Methods ==========

    async def post_alarms(self, payload: dict[str, Any]) -> None:
        """POST new alarm to Divera API.

        Args:
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_ALARM permission.
        """
        self.permissions.check(PERM_ALARM)
        _LOGGER.debug("Posting new alarm for cluster %s", self.ucr_id)
        await self._api_request(
            f"{BASE_API_V2_URL}{API_ALARM}", "POST", payload=payload
        )

    async def put_alarms(self, alarm_id: int, payload: dict[str, Any]) -> None:
        """PUT changes for existing alarm to Divera API.

        Args:
            alarm_id: Divera-Alarm-ID which needs to be changed.
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_ALARM permission.
        """
        self.permissions.check(PERM_ALARM)
        _LOGGER.debug("Updating alarm %s for cluster %s", alarm_id, self.ucr_id)
        await self._api_request(
            f"{BASE_API_V2_URL}{API_ALARM}/{alarm_id}",
            "PUT",
            payload=payload,
        )

    async def post_close_alarm(self, alarm_id: int, payload: dict[str, Any]) -> None:
        """POST to close an existing alarm to Divera API.

        Args:
            alarm_id: Divera-Alarm-ID which needs to be closed.
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_ALARM permission.
        """
        self.permissions.check(PERM_ALARM)
        _LOGGER.debug("Closing alarm %s for cluster %s", alarm_id, self.ucr_id)
        await self._api_request(
            f"{BASE_API_V2_URL}{API_ALARM}/close/{alarm_id}",
            "POST",
            payload=payload,
        )

    async def post_confirm_alarm(
        self,
        payload: dict[str, str],
        alarm_id: int,
    ) -> None:
        """POST to confirm an existing alarm to Divera API.

        Args:
            alarm_id (int): Divera-Alarm-ID which had to be confirmed.
            payload (dict): Dictionary of data to send to Divera-API.

        """

        _LOGGER.debug(
            "Posting to confirm alarm %s for cluster %s", alarm_id, self.ucr_id
        )

        self.permissions.check(PERM_ALARM)

        part_url = f"{BASE_API_V2_URL}{API_ALARM}/confirm/{alarm_id}"
        method = "POST"

        await self._api_request(part_url, method, payload=payload)

    # ========== Vehicle Methods ==========

    async def post_vehicle_status(
        self, vehicle_id: int, payload: dict[str, Any]
    ) -> None:
        """POST vehicle status and data to Divera API.

        Args:
            vehicle_id: Divera-ID of the vehicle to update.
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_STATUS_VEHICLE permission.
        """
        self.permissions.check(PERM_STATUS_VEHICLE)
        _LOGGER.debug(
            "Posting vehicle status for vehicle %s, cluster %s", vehicle_id, self.ucr_id
        )
        await self._api_request(
            f"{BASE_API_V2_URL}{API_USING_VEHICLE_SET_SINGLE}/{vehicle_id}",
            "POST",
            payload=payload,
        )

    async def get_vehicle_property(self, vehicle_id: int) -> DiveraAPIResponse:
        """GET individual vehicle properties for vehicle from Divera API.

        Args:
            vehicle_id: ID of the vehicle to fetch property data from.

        Returns:
            DiveraAPIResponse: JSON response from the API.

        Raises:
            HomeAssistantError: If user lacks PERM_STATUS_VEHICLE permission.
        """
        self.permissions.check(PERM_STATUS_VEHICLE)
        _LOGGER.debug("Getting vehicle properties for vehicle %s", vehicle_id)
        return await self._api_request(
            f"{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/get/{vehicle_id}",
            "GET",
        )

    async def post_using_vehicle_property(
        self,
        vehicle_id: int,
        payload: dict[str, Any],
    ) -> None:
        """POST individual vehicle properties for vehicle to Divera API.

        Args:
            vehicle_id: ID of the vehicle to update property data for.
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_STATUS_VEHICLE permission.
        """
        self.permissions.check(PERM_STATUS_VEHICLE)
        _LOGGER.debug(
            "Posting vehicle properties for vehicle %s, cluster %s",
            vehicle_id,
            self.ucr_id,
        )
        await self._api_request(
            f"{BASE_API_V2_URL}{API_USING_VEHICLE_PROP}/set/{vehicle_id}",
            "POST",
            payload=payload,
        )

    async def post_using_vehicle_crew(
        self,
        vehicle_id: int,
        mode: Literal["add", "remove", "reset"],
        payload: dict[str, Any],
    ) -> None:
        """POST to add, remove, or reset crew members for a vehicle.

        Args:
            vehicle_id: ID of the vehicle to modify crew for.
            mode: Mode to work with crew members:
                - "add": Adding new crew members
                - "remove": Removing specific crew members
                - "reset": Resetting all crew from vehicle
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If mode is invalid or user lacks PERM_STATUS_VEHICLE permission.
        """
        self.permissions.check(PERM_STATUS_VEHICLE)
        _LOGGER.debug(
            "Posting %s crew members to vehicle %s, cluster %s",
            mode,
            vehicle_id,
            self.ucr_id,
        )

        endpoint = f"{BASE_API_V2_URL}{API_USING_VEHICLE_CREW}/{mode}/{vehicle_id}"

        if mode in {"add", "remove"}:
            method = "POST"
        elif mode == "reset":
            method = "DELETE"
        else:
            raise HomeAssistantError(
                f"Invalid mode '{mode}' for crew management, must be 'add', 'remove', or 'reset'"
            )

        await self._api_request(endpoint, method, payload=payload)

    # ========== Message Methods ==========

    async def post_message(self, payload: dict[str, Any]) -> None:
        """POST message to Divera API.

        Args:
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_MESSAGES permission.
        """
        self.permissions.check(PERM_MESSAGES)
        _LOGGER.debug("Posting message for cluster %s", self.ucr_id)
        await self._api_request(
            f"{BASE_API_V2_URL}{API_MESSAGES}", "POST", payload=payload
        )

    # ========== News Methods ==========

    async def post_news(self, payload: dict[str, Any]) -> None:
        """POST news to Divera API.

        Args:
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_NEWS permission.
        """
        self.permissions.check(PERM_NEWS)
        _LOGGER.debug("Posting news for cluster %s", self.ucr_id)
        await self._api_request(f"{BASE_API_V2_URL}{API_NEWS}", "POST", payload=payload)

    # ========== User Status Methods ==========

    async def post_user_status(self, payload: dict[str, Any]) -> None:
        """POST user status update to Divera API.

        Args:
            payload: Dictionary of data to send to Divera-API.

        Raises:
            HomeAssistantError: If user lacks PERM_STATUS_USER permission.
        """
        self.permissions.check(PERM_STATUS_USER)
        _LOGGER.debug("Posting user status update for cluster %s", self.ucr_id)
        await self._api_request(
            f"{BASE_API_V2_URL}{API_USER_STATUS}", "POST", payload=payload
        )
