"""Coordinator for myDivera integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE_API_URL,
    D_ACCESSKEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USERNAME,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
)
from .divera_api import DiveraAPI
from .divera_data import update_data
from .utils import set_update_interval

_LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    """Manages all data handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        ucr_id: str,
    ) -> None:
        """Initialize DiveraControl coordinator.

        Each coordinator instance is associated with one user cluster relation (ucr) and handles data fetching and updates for that relation.
        The coordinator uses the access key from the relation data to authenticate with the Divera API and fetch relevant data.

        Relevant data is always fetched based on the ucr_id. But update intervals and base url are shared on cluster level, so they are stored in the main config entry and
        not in the relation data. This means that if you have multiple ucrs for the same cluster, they will share the same update intervals and base url.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            config_entry (ConfigEntry): Configuration entry for the integration.
            ucr_id (str): User cluster relation ID - basically the Divera user identification number.

        Returns:
            None

        """

        self.api = None

        self.cluster_id: str = config_entry.data.get(D_CLUSTER_ID, "")
        self.cluster_name: str = config_entry.data.get(D_CLUSTER_NAME, "")

        self.ucr_id: str = ucr_id
        self.ucr_data: dict[str, Any] = config_entry.data.get(D_RELATIONS_KEY, {}).get(
            str(ucr_id), {}
        )
        self.user_name: str = self.ucr_data.get(D_USERNAME, "")

        self.interval_data: dict[str, timedelta] = {
            D_UPDATE_INTERVAL_ALARM: timedelta(
                seconds=config_entry.data.get(
                    D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                )
            ),
            D_UPDATE_INTERVAL_DATA: timedelta(
                seconds=config_entry.data.get(
                    D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
                )
            ),
        }

        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{self.ucr_id}",
            update_interval=self.interval_data.get(D_UPDATE_INTERVAL_DATA),
            config_entry=config_entry,
        )

    async def _async_setup(self) -> None:
        """Perform initial setup tasks for the coordinator.

        This method is called during the coordinator's initialization phase and is responsible for
        performing any necessary setup tasks.

        Returns:
            None

        Raises:
            UpdateFailed: If there is an error during setup, an UpdateFailed exception will be raised with a descriptive error message.

        """

        _accesskey = self.ucr_data.get(D_ACCESSKEY)
        _base_url = self.config_entry.data.get(
            D_BASE_API_URL
        )  # no fallback to BASE_API_URL, data should be present. Also enforce error in next step.

        if not _accesskey or not _base_url:
            raise UpdateFailed(
                f"Missing relation data for user {self.user_name} (ucr_id {self.ucr_id}) in config entry data"
            )

        try:
            self.api = DiveraAPI(
                self.hass,
                self.ucr_id,
                _accesskey,
                _base_url,
            )
        except Exception as err:
            raise UpdateFailed(f"Error setting up API: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Data update by fetching data from Divera API.

        Returns:
            cluster_data (dict): The updated data dictionary with the latest Divera information.

        Raises:
            UpdateFailed: If there is an error fetching data from the API.

        """

        if self.api is None:
            raise UpdateFailed("API client not initialized")

        try:
            raw_ucr_data = await self.api.get_pull_all()
            new_cluster_data = await update_data(self.api, raw_ucr_data, self.data)

            # dynamically change update interval
            self.update_interval = set_update_interval(
                new_cluster_data, self.interval_data, self.update_interval
            )

            _LOGGER.debug(
                "Successfully updated data for unit '%s'",
                self.cluster_name,
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
        else:
            return new_cluster_data
