"""Support for Divera dynamic entities."""

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    D_CLUSTER,
    D_ALARM,
    D_MONITOR,
    D_OPEN_ALARMS,
    D_LAST_ALARM,
    D_STATUS,
    D_VEHICLE,
    DOMAIN,
    I_AVAILABILITY,
    I_CLOSED_ALARM,
    I_COUNTER_ACTIVE_ALARMS,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_PERSON,
    I_VEHICLE,
    I_FIRESTATION,
)
from .coordinator import DiveraCoordinator
from .divera_permissions import DiveraPermissions
from .entity import BaseDiveraEntity

_LOGGER = logging.getLogger(__name__)

type EntityFactory[T: BaseDiveraEntity] = Callable[[DiveraCoordinator, str], T]
type IdReader = Callable[[dict[str, Any]], set[str]]
type UniqueIdBuilder = Callable[[str, str], str]


def _coordinator_permissions(coordinator: DiveraCoordinator) -> DiveraPermissions:
    """Return the permission handler of a coordinator, tolerating mocks.

    Args:
        coordinator: Coordinator whose permissions are requested.

    Returns:
        DiveraPermissions: The coordinator's permission handler or a fresh
        (empty, fail-open for reads) instance when unavailable.
    """
    permissions = getattr(coordinator, "api", None)
    permissions = getattr(permissions, "permissions", None)
    if isinstance(permissions, DiveraPermissions):
        return permissions
    return DiveraPermissions()


class DiveraSensorManager:
    """Generic manager for dynamic entities of one platform.

    Manages the lifecycle (add/remove) of sensor entities whose set of IDs
    changes at runtime (e.g. alarms, vehicles, availability statuses).

    Args:
        coordinator: The DiveraCoordinator supplying data updates.
        async_add_entities: HA callback to register new entities.
        domain: Home Assistant domain of the managed platform (e.g.
            ``sensor``, ``select``), used for registry removal.
        get_current_ids: Callable that extracts the current set of item IDs
            from ``coordinator.data``.
        build_unique_id: Callable(ucr_id, item_id) → unique_id string used
            for registry lookups and removal.
        entity_factory: Callable(coordinator, item_id) → new entity instance.
        label: Short label used in debug log messages (e.g. "alarm").
    """

    def __init__(
        self,
        coordinator: DiveraCoordinator,
        async_add_entities: AddEntitiesCallback,
        get_current_ids: IdReader,
        build_unique_id: UniqueIdBuilder,
        entity_factory: EntityFactory,
        label: str,
        domain: str = "sensor",
    ) -> None:
        """Initialize the generic entity manager."""
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._ucr_id = coordinator.ucr_id
        self._async_add_entities = async_add_entities
        self._get_current_ids = get_current_ids
        self._build_unique_id = build_unique_id
        self._entity_factory = entity_factory
        self._label = label
        self._domain = domain
        self._known_ids: set[str] = set()
        self._unsub: Callable[[], None] | None = None

    def start(self) -> None:
        """Register coordinator listener and run an initial update."""
        if self._unsub is not None:
            return
        self._unsub = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        self._handle_coordinator_update()

    def stop(self) -> None:
        """Unregister coordinator listener."""
        if self._unsub:
            try:
                self._unsub()
            finally:
                self._unsub = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Sync known entities with the current data from the coordinator."""
        current_ids = self._get_current_ids(self.coordinator.data)

        # Remove entities whose IDs disappeared from the data
        removed_ids = self._known_ids - current_ids
        if removed_ids:
            entity_registry = er.async_get(self.hass)
            for item_id in removed_ids:
                unique_id = self._build_unique_id(self._ucr_id, item_id)
                entity_id = entity_registry.async_get_entity_id(
                    self._domain, DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed %s entity: %s", self._label, item_id)
            self._known_ids.difference_update(removed_ids)

        # Add entities for newly appearing IDs
        new_ids = current_ids - self._known_ids
        if new_ids:
            new_entities = [
                self._entity_factory(self.coordinator, item_id) for item_id in new_ids
            ]
            self._async_add_entities(new_entities, update_before_add=False)
            self._known_ids.update(new_ids)
            _LOGGER.debug("Added %d %s entities", len(new_ids), self._label)


# -------------------------------------------------------------------------------------
# Convenience constructors for specific entity types, plus the actual
# entity classes for those types
# -------------------------------------------------------------------------------------


def DiveraAvailabilitySensorManager(  # pylint: disable=invalid-name
    coordinator: DiveraCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> DiveraSensorManager:
    """Create a DiveraSensorManager pre-configured for availability sensors."""
    return DiveraSensorManager(
        coordinator=coordinator,
        async_add_entities=async_add_entities,
        get_current_ids=lambda data: (
            set()
            if not _coordinator_permissions(coordinator).has_status_permission()
            else set(data.get(D_CLUSTER, {}).get(D_STATUS, {}).keys())
        ),
        build_unique_id=lambda ucr_id, item_id: f"{ucr_id}_availability_{item_id}",
        entity_factory=DiveraAvailabilitySensor,
        label="availability",
    )


def DiveraVehicleStatusSensorManager(  # pylint: disable=invalid-name
    coordinator: DiveraCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> DiveraSensorManager:
    """Create a DiveraSensorManager for read-only vehicle status sensors.

    Only vehicles the user may not write the FMS status for get a sensor;
    vehicles with write permission are handled by the select platform.
    """
    return DiveraSensorManager(
        coordinator=coordinator,
        async_add_entities=async_add_entities,
        get_current_ids=lambda data: {
            item_id
            for item_id in data.get(D_CLUSTER, {}).get(D_VEHICLE, {}).keys()
            if not _coordinator_permissions(coordinator).can_write_vehicle_status(
                item_id
            )
        },
        build_unique_id=lambda ucr_id, item_id: f"{ucr_id}_vehicle_status_{item_id}",
        entity_factory=DiveraVehicleStatusSensor,
        label="vehicle status sensor",
    )


def DiveraUserStatusSensorManager(  # pylint: disable=invalid-name
    coordinator: DiveraCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> DiveraSensorManager:
    """Create a DiveraSensorManager for a read-only user status sensor.

    The sensor is only created when the user may not set their own status;
    users with write permission get the select entity instead.
    """
    return DiveraSensorManager(
        coordinator=coordinator,
        async_add_entities=async_add_entities,
        get_current_ids=lambda data: (
            set()
            if _coordinator_permissions(coordinator).can_write_user_status()
            else {"user_status"}
        ),
        build_unique_id=lambda ucr_id, item_id: f"{ucr_id}_{item_id}",
        entity_factory=DiveraUserStatusSensor,
        label="user status sensor",
    )


# -------------------------
# Individual Sensor Classes
# -------------------------


class DiveraUnitSensor(BaseDiveraEntity):
    """Sensor to represent a divera-unit."""

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init class DiveraUnitSensor."""
        super().__init__(coordinator)

        cluster_data = coordinator.data.get(D_CLUSTER, {})
        self.cluster_shortname = cluster_data.get("shortname", "Unknown")
        self.cluster_address = cluster_data.get("address", {"error": "no address data"})

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_name = self.cluster_name
        self._attr_unique_id = f"{self.ucr_id}_cluster"
        self._attr_icon = I_FIRESTATION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self.entity_id = f"sensor.{self.ucr_id}_cluster"

    @property
    def state(self) -> str:
        """Return the state."""
        return self.cluster_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "cluster_id": self.cluster_id,
            "shortname": self.cluster_shortname,
            **self.cluster_address,
        }


class DiveraUserSensor(BaseDiveraEntity):
    """Sensor to represent a divera-user."""

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init class DiveraUserSensor."""
        super().__init__(coordinator)

        cluster_data = coordinator.data.get(D_CLUSTER, {})
        self.cluster_shortname = cluster_data.get("shortname", "Unknown")
        self.cluster_address = cluster_data.get("address", {"error": "no address data"})

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_name = self.user_name
        self._attr_unique_id = f"{self.ucr_id}_user_cluster_relation"
        self._attr_icon = I_PERSON
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self.entity_id = f"sensor.{self.ucr_id}_user_cluster_relation"

    @property
    def state(self) -> str:
        """Return the state."""
        return self.ucr_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "ucr_id": self.ucr_id,
            "shortname": self.cluster_shortname,
            **self.cluster_address,
        }


class DiveraOpenAlarmsSensor(BaseDiveraEntity):
    """Sensor to count active alarms."""

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init class DiveraOpenAlarmsSensor."""
        super().__init__(coordinator)

        # static entity attributes
        self._attr_has_entity_name = True
        self._attr_translation_key = "open_alarms"
        self._attr_unique_id = f"{self.ucr_id}_open_alarms"
        self._attr_icon = I_COUNTER_ACTIVE_ALARMS
        self.entity_id = f"sensor.{self.ucr_id}_open_alarms"

    @property
    def state(self) -> int:
        """Return number of open alarms."""
        return self.coordinator.data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)


class DiveraAvailabilitySensor(BaseDiveraEntity):
    """Sensor to return personal status."""

    def __init__(self, coordinator: DiveraCoordinator, status_id: str) -> None:
        """Init class DiveraAvailabilitySensor."""
        super().__init__(coordinator)

        self.status_id = status_id
        self.status_name = (
            coordinator.data.get(D_CLUSTER, {})
            .get(D_STATUS, {})
            .get(status_id, {})
            .get("name", "Unknown")
        )

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_name = f"Status: {self.status_name}"
        self._attr_unique_id = f"{self.ucr_id}_availability_{status_id}"
        self._attr_icon = I_AVAILABILITY
        self.entity_id = f"sensor.{self.ucr_id}_status_{self.status_id}"

    @property
    def state(self) -> int:
        """Return the number of available members."""
        return (
            self.coordinator.data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("all", 0)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes, which are the available qualifications."""
        _monitor_qualification_data = (
            self.coordinator.data.get(D_MONITOR, {})
            .get("1", {})
            .get(self.status_id, {})
            .get("qualification", {})
        )
        _cluster_qualification_data = self.coordinator.data.get(D_CLUSTER, {}).get(
            "qualification", {}
        )
        return {
            _cluster_qualification_data[key]["shortname"]: value
            for key, value in _monitor_qualification_data.items()
            if key in _cluster_qualification_data
        }


class DiveraLastAlarmSensor(BaseDiveraEntity, RestoreEntity):
    """Sensor to represent the last alarm."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_alarm"

    def __init__(self, coordinator: DiveraCoordinator) -> None:
        """Init class DiveraLastAlarmSensor."""
        super().__init__(coordinator)

        # static entity attributes
        self._attr_unique_id = f"{self.ucr_id}_last_alarm"
        self.entity_id = f"sensor.{self.ucr_id}_last_alarm"
        self._restored_last_alarm: dict[str, Any] | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last alarm across restarts."""
        await super().async_added_to_hass()
        if self._get_last_alarm_data() is not None:
            return
        last_state = await self.async_get_last_state()
        if last_state is None or not last_state.attributes:
            return
        self._restored_last_alarm = dict(last_state.attributes)

    def _get_last_alarm_data(self) -> dict[str, Any] | None:
        """Get last alarm data safely, return None if alarm doesn't exist."""

        return (
            self.coordinator.data.get(D_ALARM, {}).get(D_LAST_ALARM)
            or self._restored_last_alarm
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if super().available and self._get_last_alarm_data() is not None:
            return True
        return False

    @property
    def state(self) -> str:
        """Return the state of the alarm."""
        if alarm_data := self._get_last_alarm_data():
            return alarm_data.get("title", "Unknown")
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the alarm."""
        return self._get_last_alarm_data() or {}

    @property
    def icon(self) -> str:
        """Return the icon of the alarm."""
        if alarm_data := self._get_last_alarm_data():
            _closed = alarm_data.get("closed", False)
            _priority = alarm_data.get("priority", False)
            return (
                I_CLOSED_ALARM
                if _closed
                else I_OPEN_ALARM if _priority else I_OPEN_ALARM_NOPRIO
            )
        return I_OPEN_ALARM_NOPRIO


class DiveraVehicleStatusSensor(BaseDiveraEntity):
    """Read-only sensor for the FMS status of a single vehicle.

    Created instead of a select entity when the user lacks the Divera
    permission to set the vehicle status, so the current status is still
    visible without implying write access.
    """

    def __init__(self, coordinator: DiveraCoordinator, vehicle_id: str) -> None:
        """Init class DiveraVehicleStatusSensor."""
        super().__init__(coordinator)

        self.vehicle_id = vehicle_id

        # static entity attributes
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{self.ucr_id}_vehicle_status_{self.vehicle_id}"
        self.entity_id = f"sensor.{self.ucr_id}_vehicle_status_{self.vehicle_id}"
        self._attr_icon = I_VEHICLE

    def _get_vehicle_data(self) -> dict[str, Any] | None:
        """Get vehicle data safely, return None if vehicle doesn't exist."""
        vehicle_items = self.coordinator.data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
        return vehicle_items.get(self.vehicle_id)

    def _get_fms_status_items(self) -> dict[str, dict[str, Any]]:
        """Get FMS status items keyed by status id (fmsstatus_id)."""
        items = (
            self.coordinator.data.get(D_CLUSTER, {})
            .get("fms_status", {})
            .get("items", {})
        )
        return {str(item_id): item for item_id, item in items.items()}

    def _status_label(self, status_id: Any) -> str:
        """Return the display label for a FMS status id."""
        if status_id is None:
            return "Unknown"
        item = self._get_fms_status_items().get(str(status_id))
        if item is None:
            return str(status_id)
        return f"{item.get('number')} - {item.get('name')}"

    @property
    def name(self) -> str:
        """Return name of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            _shortname = vehicle_data.get("shortname", "Unknown")
            _veh_name = vehicle_data.get("name", "Unknown")
            return f"{_shortname} / {_veh_name}"
        return "Unknown Vehicle"

    @property
    def available(self) -> bool:
        """Return availability of the vehicle."""
        if super().available and self._get_vehicle_data() is not None:
            return True
        return False

    @property
    def state(self) -> str:
        """Return the current FMS status label."""
        if vehicle_data := self._get_vehicle_data():
            return self._status_label(vehicle_data.get("fmsstatus_id"))
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes of the vehicle."""
        if vehicle_data := self._get_vehicle_data():
            return {"vehicle_id": self.vehicle_id, **vehicle_data}
        return {}


class DiveraUserStatusSensor(BaseDiveraEntity):
    """Read-only sensor for the user's own status.

    Created instead of a select entity when the user lacks the Divera
    permission to set their own status.
    """

    def __init__(self, coordinator: DiveraCoordinator, item_id: str) -> None:
        """Init class DiveraUserStatusSensor."""
        super().__init__(coordinator)

        # static entity attributes
        # self._attr_translation_key = "user_status"
        self._attr_unique_id = f"{self.ucr_id}_user_status"
        self.entity_id = f"sensor.{self.ucr_id}_user_status"
        self._attr_has_entity_name = True
        self._attr_icon = I_AVAILABILITY

    def _get_status_items(self) -> dict[str, dict[str, Any]]:
        """Get user status mapping from coordinator data."""
        statuses = self.coordinator.data.get(D_CLUSTER, {}).get(D_STATUS, {})
        return {str(key): value for key, value in statuses.items()}

    def _status_label(self, status_id: Any) -> str:
        """Return the display label for a status id."""
        if status_id is None:
            return "Unknown"
        status = self._get_status_items().get(str(status_id))
        if status is None:
            return str(status_id)
        return str(status.get("name", status_id))

    @property
    def state(self) -> str:
        """Return the current user status label."""
        status_id = self.coordinator.data.get("status", {}).get("status_id")
        return self._status_label(status_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes of the user status."""
        status_data = self.coordinator.data.get("status", {})
        return {
            "status_id": status_data.get("status_id"),
            "note": status_data.get("note", ""),
            "vehicle": status_data.get("vehicle", 0),
        }
