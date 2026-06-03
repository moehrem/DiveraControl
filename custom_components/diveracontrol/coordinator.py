"""Coordinator for myDivera integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE_API_URL,
    D_API_KEY,
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

    @staticmethod
    def _get_relation_from_data(
        config_entry: ConfigEntry, ucr_id: str
    ) -> dict[str, Any]:
        """Return relation data for a given ucr_id from config entry data."""

        relations = config_entry.data.get(D_RELATIONS_KEY, {})
        if not isinstance(relations, dict):
            return {}

        relation = relations.get(str(ucr_id), {})
        if isinstance(relation, dict):
            return dict(relation)
        return {}

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        ucr_id: str,
    ) -> None:
        """Initialize DiveraControl coordinator.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            config_entry (ConfigEntry): Configuration entry for the integration.
            ucr_id (str): User relation ID.

        Returns:
            None

        """

        self.api = None

        self.cluster_id: str = config_entry.data.get(D_CLUSTER_ID, "")
        self.cluster_name: str = config_entry.data.get(D_CLUSTER_NAME, "")

        user_cluster_relation_data = self._get_relation_from_data(config_entry, ucr_id)
        self.ucr_id: str = user_cluster_relation_data.get(D_UCR_ID, ucr_id)
        self.user_name: str = user_cluster_relation_data.get(D_USERNAME, "")

        self._initial_raw_ucr_data: dict[str, Any] | None = None

        self.interval_data = {
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

        user_cluster_relation_data = self._get_relation_from_data(
            self.config_entry, self.ucr_id
        )
        _api_key = user_cluster_relation_data.get(D_API_KEY)
        _base_url = self.config_entry.data.get(D_BASE_API_URL, BASE_API_URL)

        if not _api_key or not _base_url:
            raise UpdateFailed(
                f"Missing relation data for ucr_id {self.ucr_id} in config entry data"
            )

        try:
            self.api = DiveraAPI(
                self.hass,
                self.ucr_id,
                _api_key,
                _base_url,
            )
        except Exception as err:
            raise UpdateFailed(f"Error setting up API: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API.

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
