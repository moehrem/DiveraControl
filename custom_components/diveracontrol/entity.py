"""Contains all base divera entity classes."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DiveraCoordinator
from .utils import get_user_device_info


class BaseDiveraEntity(CoordinatorEntity):
    """Base class for DiveraControl entities."""

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init base class."""
        super().__init__(coordinator)

        self.ucr_id = coordinator.ucr_id
        self.cluster_name = coordinator.cluster_name
        self.user_name = coordinator.user_name

        self._attr_device_info = get_user_device_info(self.ucr_id, self.user_name)
