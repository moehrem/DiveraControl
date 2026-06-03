"""Contains all base divera entity classes."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BASE_API_URL,
    CONF_URL,
    D_CLUSTER,
    D_SHORTNAME,
    D_USER,
    DOMAIN,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)
from .coordinator import DiveraCoordinator

# from .utils import get_user_device_info


class BaseDiveraEntity(CoordinatorEntity):
    """Base class for DiveraControl entities."""

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init base class."""
        super().__init__(coordinator)

        self.cluster_id = coordinator.cluster_id
        self.cluster_name = coordinator.cluster_name
        self.ucr_id = coordinator.ucr_id
        self.user_name = coordinator.user_name

        self.user_shortname = coordinator.data.get(D_USER, {}).get(
            D_SHORTNAME, self.user_name
        )
        self.cluster_shortname = coordinator.data.get(D_CLUSTER, {}).get(
            D_SHORTNAME, self.cluster_name
        )

        self._attr_device_info = self._get_device_info()

    def _get_device_info(self) -> DeviceInfo:
        """Return device info for the cluster hub."""

        return {
            "identifiers": {(DOMAIN, self.cluster_id)},
            "configuration_url": f"{BASE_API_URL}{CONF_URL}",
            "model": "Divera Cluster",
            "model_id": self.cluster_id,
            "name": self.cluster_name,
            "manufacturer": "Divera 24/7",
            "sw_version": f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        }
