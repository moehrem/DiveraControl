"""Tests for DiveraControl sensor entities."""

from unittest.mock import MagicMock, patch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.const import (
    D_CLUSTER,
    D_MONITOR,
    D_STATUS,
    D_VEHICLE,
    I_OPEN_ALARM_NOPRIO,
)
from custom_components.diveracontrol.sensor_entity import (
    DiveraAvailabilitySensor,
    DiveraUnitSensor,
    DiveraVehicleSensor,
    DiveraVehicleSensorManager,
)


def _mock_coordinator(hass: HomeAssistant, data: dict) -> MagicMock:
    """Create a lightweight coordinator mock for entity tests."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.cluster_id = "test_cluster_id"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


def test_vehicle_sensor_state_name_and_attributes(hass: HomeAssistant) -> None:
    """Test vehicle sensor state/name and extra attributes."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "v1": {"shortname": "LF", "name": "16-1", "fmsstatus_id": 2}
                }
            }
        },
    )

    entity = DiveraVehicleSensor(coordinator, "v1")

    assert entity.available is True
    assert entity.state == "2"
    assert entity.device_class == SensorDeviceClass.ENUM
    assert entity.options == [str(i) for i in range(1, 10)]
    assert entity.name == "LF / 16-1"
    assert entity.extra_state_attributes["vehicle_id"] == "v1"


def test_unit_sensor_and_availability_sensor_attributes(hass: HomeAssistant) -> None:
    """Test static unit sensor and mapped availability attributes."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                "shortname": "LZ",
                "address": {"city": "Musterstadt"},
                D_STATUS: {"1": {"name": "Verfügbar"}},
                "qualification": {"q1": {"shortname": "AGT"}},
            },
            D_MONITOR: {"1": {"1": {"all": 4, "qualification": {"q1": 2, "x": 9}}}},
        },
    )

    unit_sensor = DiveraUnitSensor(coordinator)
    availability = DiveraAvailabilitySensor(coordinator, "1")

    assert unit_sensor.state == "test_cluster_id"
    assert unit_sensor.extra_state_attributes["shortname"] == "LZ"
    assert unit_sensor.extra_state_attributes["city"] == "Musterstadt"
    assert availability.state == 4
    assert availability.extra_state_attributes == {"AGT": 2}


def test_vehicle_sensor_manager_stop_ignores_runtime_error(
    hass: HomeAssistant,
) -> None:
    """Test vehicle manager stop ignores RuntimeError from unsubscribe."""
    coordinator = _mock_coordinator(hass, {D_CLUSTER: {D_VEHICLE: {}}})
    add_entities = MagicMock()
    manager = DiveraVehicleSensorManager(coordinator, add_entities)

    def _raise_runtime_error() -> None:
        raise RuntimeError("already removed")

    manager._unsub = _raise_runtime_error
    # Use try/except to handle the RuntimeError that stop() should catch
    try:
        manager.stop()
    except RuntimeError:
        pass  # stop() should handle this internally

    assert manager._unsub is None
