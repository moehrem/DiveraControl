"""Definition of Home Assistant Sensors for the Divera Integration.

Responsibilities:
- Subscribe to data from the DataUpdateCoordinator (per HUB).
- Provide sensor data (state, extra_state_attributes, etc.) for Home Assistant.
- Handle attributes such as unique_id, name, etc., required for sensor integration.
- Adding and removing of sensors.

Communication:
- Retrieves data from the DataUpdateCoordinator (per HUB).
- Delivers data to Home Assistant for display in the user interface or use in automations.


"""

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.entity_registry as er

from .const import (
    D_ACTIVE_ALARM_COUNT,
    D_ALARM,
    # D_ALARMS,
    # D_VEHICLE_STATUS,
    D_CLUSTER_ADDRESS,
    D_COORDINATOR,
    D_DATA,
    D_CLUSTER_ID,
    # new structure
    D_STATUS,
    D_STATUS_CONF,
    D_UCR,
    D_VEHICLE,
    D_UCR_ID,
    D_USER,
    DOMAIN,
    I_CLOSED_ALARM,
    I_COUNTER_ACTIVE_ALARMS,
    I_FIRESTATION,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_STATUS,
    I_VEHICLE,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
)
from .utils import BaseDiveraEntity, get_device_info

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up the Divera sensors."""

    cluster = config_entry.data
    cluster_id = cluster[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]

    async def sync_sensors():
        """Synchronize all sensors with the current data from coordinator."""

        cluster_data = coordinator.cluster_data
        current_sensors = hass.data[DOMAIN][cluster_id].setdefault("sensors", {})
        new_sensors = []

        new_alarm_data = cluster_data.get(D_ALARM, {})
        new_vehicle_data = cluster_data.get(D_VEHICLE, {})
        new_static_sensors_data = {
            D_ACTIVE_ALARM_COUNT,
            D_CLUSTER_ADDRESS,
            D_STATUS,
        }

        if isinstance(new_alarm_data, dict):
            new_alarm_data = set(new_alarm_data.keys())
        else:
            new_alarm_data = set()

        if isinstance(new_vehicle_data, dict):
            new_vehicle_data = set(new_vehicle_data.keys())
        else:
            new_vehicle_data = set()

        # adding static sensors
        static_sensor_map = {
            D_ACTIVE_ALARM_COUNT: DiveraOpenAlarmsSensor(
                coordinator, cluster_data, cluster_id
            ),
            D_CLUSTER_ADDRESS: DiveraUnitSensor(coordinator, cluster_data, cluster_id),
        }

        for sensor_name, sensor_instance in static_sensor_map.items():
            if sensor_name not in current_sensors:
                new_sensors.append(sensor_instance)
                current_sensors[sensor_name] = sensor_instance

        # adding alarm sensors
        new_alarms = new_alarm_data - current_sensors.keys()
        for alarm_id in new_alarms:
            sensor = DiveraAlarmSensor(coordinator, cluster_data, alarm_id, cluster_id)
            new_sensors.append(sensor)
            current_sensors[alarm_id] = sensor

        # adding behicle sensors
        new_vehicles = new_vehicle_data - current_sensors.keys()
        for vehicle_id in new_vehicles:
            sensor = DiveraVehicleSensor(
                coordinator, cluster_data, vehicle_id, cluster_id
            )
            new_sensors.append(sensor)
            current_sensors[vehicle_id] = sensor

        # remove outdated sensors
        active_ids = new_alarm_data | new_vehicle_data | new_static_sensors_data
        removable_sensors = set(current_sensors.keys() - active_ids)
        for sensor_id in removable_sensors:
            sensor = current_sensors.pop(sensor_id, None)
            if sensor:
                await sensor.remove_from_hass()
                LOGGER.debug("Removed sensor: %s", sensor_id)

        # register new sensors
        if new_sensors:
            async_add_entities(new_sensors, update_before_add=True)

    await sync_sensors()

    # adding listener for updates
    coordinator.async_add_listener(lambda: asyncio.create_task(sync_sensors()))


async def async_remove_sensors(hass: HomeAssistant, cluster_id: str) -> None:
    """Remove all sensors for a specific HUB."""
    if DOMAIN in hass.data and cluster_id in hass.data[DOMAIN]:
        sensors = hass.data[DOMAIN][cluster_id].get("sensors", {})
        for sensor_id, sensor in sensors.items():
            sensor.remove_from_hass()
            LOGGER.info("Removed sensor: %s for HUB: %s", sensor_id, cluster_id)

        # remove sensor list
        hass.data[DOMAIN][cluster_id].pop("sensors", None)


class BaseDiveraSensor(Entity, BaseDiveraEntity):
    """Basisklasse für Divera-Sensoren."""

    def __init__(self, coordinator, cluster_data, cluster_id: str) -> None:
        """Initialisiert einen Sensor."""
        Entity.__init__(self)
        BaseDiveraEntity.__init__(self, coordinator, cluster_data, cluster_id)

        self.ucr_id = cluster_data.get(D_UCR_ID, "")
        self.cluster_name = (
            cluster_data.get(D_UCR, {}).get(self.ucr_id, {}).get("name", "Unit Unknown")
        )

    @property
    def device_info(self):
        """Fetch device info."""
        return get_device_info(self.cluster_name)


class DiveraAlarmSensor(BaseDiveraSensor):
    """Sensor to represent a single alarm."""

    def __init__(
        self, coordinator, cluster_data, alarm_id: str, cluster_id: str
    ) -> None:
        """Init class DiveraAlarmSensor."""
        super().__init__(coordinator, cluster_data, cluster_id)
        self.alarm_id = alarm_id
        self.alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_alarm_{self.alarm_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique ID of sensor."""
        return f"{self.cluster_id}_alarm_{self.alarm_id}"

    @property
    def name(self) -> str:
        """Name of sensor."""
        return f"Alarm {self.alarm_id}"

    @property
    def state(self) -> str:
        """State of sensor."""
        # alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
        return self.alarm_data.get("title", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        return self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        # alarm_data = self.cluster_data.get(D_ALARM, {}).get(self.alarm_id, {})
        closed = self.alarm_data.get("closed", False)
        priority = self.alarm_data.get("priority", False)
        if closed:
            return I_CLOSED_ALARM
        if priority:
            return I_OPEN_ALARM

        return I_OPEN_ALARM_NOPRIO


class DiveraVehicleSensor(BaseDiveraSensor):
    """Sensor to represent a single vehicle."""

    def __init__(
        self, coordinator, cluster_data, vehicle_id: str, cluster_id: str
    ) -> None:
        """Init class DiveraVehicleSensor."""
        super().__init__(coordinator, cluster_data, cluster_id)
        self._vehicle_id = vehicle_id

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_vehicle_{self._vehicle_id}'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique if if sensor."""
        return f"{self.cluster_id}_vehicle_{self._vehicle_id}"

    @property
    def name(self) -> str:
        """Name of sensor."""
        vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        shortname = vehicle_data.get("shortname", "Unknown")
        veh_name = vehicle_data.get("name", "Unknown")
        return f"{shortname} / {veh_name} "

    @property
    def state(self) -> str:
        """State of sensor."""
        vehicle_data = self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        return vehicle_data.get("fmsstatus_id", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        extra_state_attributes = {}
        extra_state_attributes["Vehicle-ID"] = self._vehicle_id
        extra_state_attributes.update(
            self.cluster_data.get(D_VEHICLE, {}).get(self._vehicle_id, {})
        )
        return extra_state_attributes

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_VEHICLE


class DiveraUnitSensor(BaseDiveraSensor):
    """Sensor to represent a divera-unit."""

    def __init__(self, coordinator, cluster_data, cluster_id: str) -> None:
        """Init class DiveraUnitSensor."""
        super().__init__(coordinator, cluster_data, cluster_id)
        self.fs_name = next(
            iter(cluster_data.get(D_CLUSTER_ADDRESS, {}).keys()), "Unknown"
        )

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_cluster_address'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"{self.cluster_id}_cluster_address"

    @property
    def name(self) -> str:
        """Name of sensor.."""
        return next(
            iter(self.cluster_data.get(D_CLUSTER_ADDRESS, {}).keys()),
            "Unknown",
        )

    @property
    def state(self) -> str:
        """State of sensor."""
        return self.cluster_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes of sensor."""
        firestation_data = self.cluster_data.get(D_CLUSTER_ADDRESS, {}).get(
            self.fs_name, {}
        )
        address = firestation_data.get("address", {})
        return {
            "cluster_id": self.cluster_id,
            "shortname": firestation_data.get("shortname", "Unknown"),
            "latitude": address.get("lat"),
            "longitude": address.get("lng"),
            "street": address.get("street"),
            "zip": address.get("zip"),
            "city": address.get("city"),
            "country": address.get("country"),
            "ags": address.get("ags"),
        }

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_FIRESTATION


class DiveraOpenAlarmsSensor(BaseDiveraSensor):
    """Sensor to count active alarms."""

    def __init__(self, coordinator, cluster_data, cluster_id: str) -> None:
        """Init class DiveraOpenAlarmsSensor."""
        super().__init__(coordinator, cluster_data, cluster_id)

    @property
    def entity_id(self) -> str:
        """Entity-ID of sensor."""
        return f"sensor.{f'{self.cluster_id}_open_alarms'}"

    @entity_id.setter
    def entity_id(self, value: str) -> None:
        """Set entity-id of sensor."""
        self._entity_id = value

    @property
    def unique_id(self) -> str:
        """Unique-ID of sensor."""
        return f"{self.cluster_id}_open_alarms"

    @property
    def name(self) -> str:
        """Name of sensor."""
        # return f"Open Alarms {self.cluster_id}"
        return "Open Alarms"

    @property
    def state(self) -> int:
        """State of sensor."""
        try:
            return int(self.cluster_data.get(D_ACTIVE_ALARM_COUNT, 0))
        except (ValueError, TypeError):
            return 0

    @property
    def icon(self) -> str:
        """Icon of sensor."""
        return I_COUNTER_ACTIVE_ALARMS
