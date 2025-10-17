"""Contains all base divera entity classes."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DiveraCoordinator
from .utils import get_device_info


class BaseDiveraEntity(CoordinatorEntity):
    """Base class for DiveraControl entities."""

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init base class."""
        super().__init__(coordinator)

        self.ucr_id = coordinator.ucr_id
        self.cluster_name = coordinator.cluster_name

        self._attr_device_info = get_device_info(self.cluster_name)
