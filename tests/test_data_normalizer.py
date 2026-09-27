"""Tests for DiveraControl data normalizers."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.diveracontrol.data_normalizer import (
    CrewIDNormalizer,
    DateTimeNormalizer,
    DeviceIdNormalizer,
    FieldNormalizer,
    IntListNormalizer,
    IntNormalizer,
    ServiceDataNormalizer,
    StrListNormalizer,
    VehicleIdNormalizer,
    normalize_service_call_data,
)


class TestDeviceIdNormalizer:
    """Test DeviceIdNormalizer class."""

    def test_normalize_string(self) -> None:
        """Test normalizing a string device_id."""
        normalizer = DeviceIdNormalizer("device_id")
        result = normalizer.normalize("test_device")
        assert result == "test_device"

    def test_normalize_list_single_item(self) -> None:
        """Test normalizing a list with single device_id."""
        normalizer = DeviceIdNormalizer("device_id")
        result = normalizer.normalize(["test_device"])
        assert result == "test_device"

    def test_normalize_list_multiple_items_raises(self) -> None:
        """Test that list with multiple items raises ServiceValidationError."""
        normalizer = DeviceIdNormalizer("device_id")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize(["device1", "device2"])

    def test_normalize_none_raises(self) -> None:
        """Test that None raises ServiceValidationError."""
        normalizer = DeviceIdNormalizer("device_id")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize(None)

    def test_normalize_empty_string_raises(self) -> None:
        """Test that empty string raises ServiceValidationError."""
        normalizer = DeviceIdNormalizer("device_id")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize("")

    def test_normalize_invalid_type_raises(self) -> None:
        """Test that invalid type raises ServiceValidationError."""
        normalizer = DeviceIdNormalizer("device_id")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize(123)


class TestIntListNormalizer:
    """Test IntListNormalizer class."""

    def test_normalize_list_of_ints(self) -> None:
        """Test normalizing a list of integers."""
        normalizer = IntListNormalizer("field")
        result = normalizer.normalize([1, 2, 3])
        assert result == [1, 2, 3]

    def test_normalize_list_of_strings(self) -> None:
        """Test normalizing a list of string numbers."""
        normalizer = IntListNormalizer("field")
        result = normalizer.normalize(["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_normalize_comma_separated_string(self) -> None:
        """Test normalizing a comma-separated string."""
        normalizer = IntListNormalizer("field")
        result = normalizer.normalize("1,2,3")
        assert result == [1, 2, 3]

    def test_normalize_single_int_string(self) -> None:
        """Test normalizing a single integer string."""
        normalizer = IntListNormalizer("field")
        result = normalizer.normalize("42")
        assert result == [42]

    def test_normalize_none(self) -> None:
        """Test normalizing None returns empty list."""
        normalizer = IntListNormalizer("field")
        result = normalizer.normalize(None)
        assert result == []

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string returns empty list."""
        normalizer = IntListNormalizer("field")
        result = normalizer.normalize("")
        assert result == []

    def test_normalize_invalid_string_raises(self) -> None:
        """Test that invalid string raises ServiceValidationError."""
        normalizer = IntListNormalizer("field")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize("not_a_number")

    def test_normalize_invalid_list_raises(self) -> None:
        """Test that list with invalid items raises ServiceValidationError."""
        normalizer = IntListNormalizer("field")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize(["1", "not_a_number"])


class TestCrewIDNormalizer:
    """Test CrewIDNormalizer class."""

    def test_normalize_list_of_ints(self) -> None:
        """Test normalizing a list of crew IDs."""
        normalizer = CrewIDNormalizer("crew")
        result = normalizer.normalize([1, 2, 3])
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_normalize_list_of_strings(self) -> None:
        """Test normalizing a list of string crew IDs."""
        normalizer = CrewIDNormalizer("crew")
        result = normalizer.normalize(["1", "2", "3"])
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_normalize_single_int_string(self) -> None:
        """Test normalizing a single integer as string."""
        normalizer = CrewIDNormalizer("crew")
        result = normalizer.normalize("42")
        assert result == [{"id": 42}]

    def test_normalize_single_string(self) -> None:
        """Test normalizing a single string crew ID."""
        normalizer = CrewIDNormalizer("crew")
        result = normalizer.normalize("42")
        assert result == [{"id": 42}]

    def test_normalize_comma_separated_string(self) -> None:
        """Test normalizing a comma-separated string of crew IDs."""
        normalizer = CrewIDNormalizer("crew")
        result = normalizer.normalize("1,2,3")
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_normalize_none(self) -> None:
        """Test normalizing None returns empty list."""
        normalizer = CrewIDNormalizer("crew")
        result = normalizer.normalize(None)
        assert result == []


class TestStrListNormalizer:
    """Test StrListNormalizer class."""

    def test_normalize_list_of_strings(self) -> None:
        """Test normalizing a list of strings."""
        normalizer = StrListNormalizer("field")
        result = normalizer.normalize(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_normalize_comma_separated_string(self) -> None:
        """Test normalizing a comma-separated string."""
        normalizer = StrListNormalizer("field")
        result = normalizer.normalize("a,b,c")
        assert result == ["a", "b", "c"]

    def test_normalize_none(self) -> None:
        """Test normalizing None returns empty list."""
        normalizer = StrListNormalizer("field")
        result = normalizer.normalize(None)
        assert result == []


class TestIntNormalizer:
    """Test IntNormalizer class."""

    def test_normalize_int(self) -> None:
        """Test normalizing an integer."""
        normalizer = IntNormalizer("field")
        result = normalizer.normalize(42)
        assert result == 42

    def test_normalize_string(self) -> None:
        """Test normalizing a string integer."""
        normalizer = IntNormalizer("field")
        result = normalizer.normalize("42")
        assert result == 42

    def test_normalize_none(self) -> None:
        """Test normalizing None returns None."""
        normalizer = IntNormalizer("field")
        result = normalizer.normalize(None)
        assert result is None

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string returns None."""
        normalizer = IntNormalizer("field")
        result = normalizer.normalize("")
        assert result is None

    def test_normalize_invalid_string_raises(self) -> None:
        """Test that invalid string raises ServiceValidationError."""
        normalizer = IntNormalizer("field")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize("not_a_number")


class TestVehicleIdNormalizer:
    """Test VehicleIdNormalizer class."""

    def test_normalize_list_of_ints(self) -> None:
        """Test normalizing a list of vehicle IDs."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        result = normalizer.normalize([1, 2, 3])
        assert result == [1, 2, 3]

    def test_normalize_list_of_strings(self) -> None:
        """Test normalizing a list of string vehicle IDs."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        result = normalizer.normalize(["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_normalize_entity_id_format(self) -> None:
        """Test normalizing entity IDs like 'sensor.vehicle_123456'."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        result = normalizer.normalize("sensor.vehicle_123456")
        assert result == [123456]

    def test_normalize_single_int_string(self) -> None:
        """Test normalizing a single integer as string."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        result = normalizer.normalize("42")
        assert result == [42]

    def test_normalize_comma_separated_string(self) -> None:
        """Test normalizing a comma-separated string of vehicle IDs."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        result = normalizer.normalize("1,2,3")
        assert result == [1, 2, 3]

    def test_normalize_none(self) -> None:
        """Test normalizing None returns empty list."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        result = normalizer.normalize(None)
        assert result == []

    def test_normalize_invalid_format_raises(self) -> None:
        """Test that invalid format raises ServiceValidationError."""
        normalizer = VehicleIdNormalizer("vehicle_id")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize("invalid_id")


class TestDateTimeNormalizer:
    """Test DateTimeNormalizer class."""

    def test_normalize_int_timestamp(self) -> None:
        """Test normalizing an integer Unix timestamp."""
        normalizer = DateTimeNormalizer("ts")
        timestamp = 1700000000
        result = normalizer.normalize(timestamp)
        assert result == timestamp
        assert isinstance(result, int)

    def test_normalize_string_timestamp(self) -> None:
        """Test normalizing a string Unix timestamp."""
        normalizer = DateTimeNormalizer("ts")
        timestamp = "1700000000"
        result = normalizer.normalize(timestamp)
        assert result == 1700000000
        assert isinstance(result, int)

    def test_normalize_datetime_object(self) -> None:
        """Test normalizing a datetime object."""
        normalizer = DateTimeNormalizer("ts")
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = normalizer.normalize(dt)
        assert isinstance(result, int)
        # Should be approximately the Unix timestamp for 2024-01-01 12:00:00
        assert result > 0

    def test_normalize_iso_format_string(self) -> None:
        """Test normalizing an ISO format datetime string."""
        normalizer = DateTimeNormalizer("ts")
        iso_string = "2024-01-01T12:00:00Z"
        result = normalizer.normalize(iso_string)
        assert isinstance(result, int)
        assert result > 0

    def test_normalize_none(self) -> None:
        """Test normalizing None returns None."""
        normalizer = DateTimeNormalizer("ts")
        result = normalizer.normalize(None)
        assert result is None

    def test_normalize_invalid_string_raises(self) -> None:
        """Test that invalid datetime string raises ServiceValidationError."""
        normalizer = DateTimeNormalizer("ts")
        with pytest.raises(ServiceValidationError):
            normalizer.normalize("not_a_date")


class TestServiceDataNormalizer:
    """Test ServiceDataNormalizer class."""

    def test_normalize_with_device_id_string(self) -> None:
        """Test normalizing data with device_id as string."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": "test_device"}
        result = normalizer.normalize(data)
        assert result["device_id"] == "test_device"

    def test_normalize_with_device_id_list(self) -> None:
        """Test normalizing data with device_id as list."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": ["test_device"]}
        result = normalizer.normalize(data)
        assert result["device_id"] == "test_device"

    def test_normalize_missing_device_id_raises(self) -> None:
        """Test that missing device_id raises ServiceValidationError."""
        normalizer = ServiceDataNormalizer()
        data = {"status": "1"}
        with pytest.raises(ServiceValidationError):
            normalizer.normalize(data)

    def test_normalize_empty_device_id_raises(self) -> None:
        """Test that empty device_id raises ServiceValidationError."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": ""}
        with pytest.raises(ServiceValidationError):
            normalizer.normalize(data)

    def test_normalize_vehicle_field(self) -> None:
        """Test normalizing vehicle field."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": "test_device", "vehicle": "1,2,3"}
        result = normalizer.normalize(data)
        # vehicle uses VehicleIdNormalizer which returns list[int]
        assert result["vehicle"] == [1, 2, 3]

    def test_normalize_group_field(self) -> None:
        """Test normalizing group field."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": "test_device", "group": ["1", "2", "3"]}
        result = normalizer.normalize(data)
        assert result["group"] == [1, 2, 3]

    def test_normalize_status_field(self) -> None:
        """Test normalizing status field."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": "test_device", "status": "42"}
        result = normalizer.normalize(data)
        assert result["status"] == 42

    def test_normalize_datetime_field(self) -> None:
        """Test normalizing datetime field."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": "test_device", "ts_archive": "1700000000"}
        result = normalizer.normalize(data)
        assert result["ts_archive"] == 1700000000
        assert isinstance(result["ts_archive"], int)

    def test_normalize_crew_field(self) -> None:
        """Test normalizing crew field."""
        normalizer = ServiceDataNormalizer()
        data = {"device_id": "test_device", "crew": "1,2,3"}
        result = normalizer.normalize(data)
        # crew uses IntListNormalizer in ServiceDataNormalizer, not CrewIDNormalizer
        assert result["crew"] == [1, 2, 3]

    def test_normalize_multiple_fields(self) -> None:
        """Test normalizing multiple fields at once."""
        normalizer = ServiceDataNormalizer()
        data = {
            "device_id": "test_device",
            "vehicle": ["1", "2"],
            "status": "5",
            "group": "10,20",
        }
        result = normalizer.normalize(data)
        assert result["device_id"] == "test_device"
        assert result["vehicle"] == [1, 2]
        assert result["status"] == 5
        assert result["group"] == [10, 20]


class TestNormalizeServiceCallData:
    """Test the module-level normalize_service_call_data function."""

    def test_normalize_basic_data(self) -> None:
        """Test normalizing basic service call data."""
        data = {"device_id": "test_device", "status": "1"}
        result = normalize_service_call_data(data)
        assert result["device_id"] == "test_device"
        assert result["status"] == 1

    def test_normalize_with_all_fields(self) -> None:
        """Test normalizing data with all supported fields."""
        data = {
            "device_id": ["test_device"],
            "vehicle": "1,2,3",
            "crew": [1, 2],  # Will be normalized by IntListNormalizer
            "group": ["10"],
            "status": "5",
            "ts_archive": "1700000000",
            "ts_publish": "1700000001",
        }
        result = normalize_service_call_data(data)
        assert result["device_id"] == "test_device"
        assert result["vehicle"] == [1, 2, 3]
        # crew is normalized by IntListNormalizer in ServiceDataNormalizer
        assert result["crew"] == [1, 2]
        assert result["group"] == [10]
        assert result["status"] == 5
        assert result["ts_archive"] == 1700000000
        assert result["ts_publish"] == 1700000001
