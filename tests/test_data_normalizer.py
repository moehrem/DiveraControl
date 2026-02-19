"""Tests for service data normalization."""

from datetime import datetime

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.diveracontrol.data_normalizer import normalize_service_call_data


def test_normalize_service_call_data_success_mixed_types() -> None:
    """Test normalization of mixed field types used by services."""
    data = {
        "device_id": ["device_1"],
        "group": "1, 2,3",
        "status": "4",
        "vehicle_id": ["sensor.vehicle_123", 456],
        "ts_publish": "2024-01-01T12:30:00+00:00",
    }

    normalized = normalize_service_call_data(data)

    assert normalized["device_id"] == "device_1"
    assert normalized["group"] == [1, 2, 3]
    assert normalized["status"] == 4
    assert normalized["vehicle_id"] == [123, 456]
    assert isinstance(normalized["ts_publish"], int)


def test_normalize_service_call_data_missing_device_id() -> None:
    """Test missing device_id raises translation-aware validation error."""
    with pytest.raises(ServiceValidationError) as exc_info:
        normalize_service_call_data({"group": "1,2"})

    assert exc_info.value.translation_key == "no_device_id"


def test_normalize_service_call_data_multiple_devices_not_allowed() -> None:
    """Test device_id list with multiple entries raises expected error."""
    with pytest.raises(ServiceValidationError) as exc_info:
        normalize_service_call_data({"device_id": ["a", "b"]})

    assert exc_info.value.translation_key == "service_wrong_devices_count"
    assert exc_info.value.translation_placeholders == {"num_devices": "2"}


def test_normalize_service_call_data_invalid_int_list_format() -> None:
    """Test invalid integer list values raise proper validation error."""
    with pytest.raises(ServiceValidationError) as exc_info:
        normalize_service_call_data({"device_id": "device_1", "group": "1,x,3"})

    assert exc_info.value.translation_key == "invalid_id_format"


def test_normalize_service_call_data_crew_mixed_inputs() -> None:
    """Test crew field supports mixed int and comma-separated string values."""
    normalized = normalize_service_call_data(
        {
            "device_id": "device_1",
            "crew": [1, "2", "4"],
        }
    )

    assert normalized["crew"] == [1, 2, 4]


def test_normalize_service_call_data_invalid_vehicle_id() -> None:
    """Test invalid vehicle ID raises translation-aware validation error."""
    with pytest.raises(ServiceValidationError) as exc_info:
        normalize_service_call_data(
            {"device_id": "device_1", "vehicle_id": ["sensor.vehicle_x"]}
        )

    assert exc_info.value.translation_key == "invalid_vehicle_id_format"


def test_normalize_service_call_data_datetime_inputs() -> None:
    """Test datetime normalizer accepts datetime objects and unix strings."""
    timestamp_value = datetime(2024, 1, 1, 0, 0, 0)
    normalized = normalize_service_call_data(
        {
            "device_id": "device_1",
            "ts_archive": timestamp_value,
            "newssurvey_ts_response": "1704067200",
        }
    )

    assert normalized["ts_archive"] == int(timestamp_value.timestamp())
    assert normalized["newssurvey_ts_response"] == 1704067200


def test_normalize_service_call_data_invalid_datetime_type() -> None:
    """Test unsupported datetime input type raises validation error."""
    with pytest.raises(ServiceValidationError) as exc_info:
        normalize_service_call_data({"device_id": "device_1", "ts_publish": [1, 2]})

    assert exc_info.value.translation_key == "invalid_datetime_type"
