"""Service data normalizers for handling inconsistent frontend formats.

This is needed as different action calls from frontend, developer tools or automations may send data
with different format. This is to ensure a consistent format for further processing.

"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.dt import parse_datetime

from .const import DOMAIN


class FieldNormalizer(ABC):
    """Base class for field normalization."""

    def __init__(self, field_name: str) -> None:
        """Initialize normalizer.

        Args:
            field_name: Name of the field to normalize

        """
        self.field_name = field_name

    @abstractmethod
    def normalize(self, value: Any) -> Any:
        """Normalize the field value.

        Args:
            value: Raw value from service call

        Returns:
            Normalized value

        Raises:
            ServiceValidationError: If value cannot be normalized

        """

    # def _raise_error(self, translation_key: str, **placeholders: Any) -> None:
    #     """Raise a ServiceValidationError with translation.

    #     Args:
    #         translation_key: Translation key for error message
    #         **placeholders: Additional placeholders for translation

    #     Raises:
    #         ServiceValidationError: Always raised

    #     """
    #     raise ServiceValidationError(
    #         translation_domain=DOMAIN,
    #         translation_key=translation_key,
    #         translation_placeholders={"field": self.field_name, **placeholders},
    #     )


class DeviceIdNormalizer(FieldNormalizer):
    """Normalize device_id to single string."""

    def normalize(self, value: str | list[str] | None) -> str:
        """Normalize device_id to single string.

        Args:
            value: Device ID as string, list, or None

        Returns:
            Single device ID string

        Raises:
            ServiceValidationError: If invalid format

        """
        if not value:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_device_id",
            )

        # Normalize to string
        if isinstance(value, list):
            if len(value) != 1:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="service_wrong_devices_count",
                    translation_placeholders={"num_devices": str(len(value))},
                )
            return value[0]

        if isinstance(value, str):
            return value

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_field_type",
            translation_placeholders={
                "field": self.field_name,
                "expected_type": "string or list",
                "type": type(value).__name__,
            },
        )


class IntListNormalizer(FieldNormalizer):
    """Normalize comma-separated strings or lists to list of integers."""

    def normalize(self, value: str | list[int | str] | None) -> list[int]:
        """Normalize to list of integers.

        Args:
            value: String, list, or None

        Returns:
            List of integers

        Raises:
            ServiceValidationError: If invalid format

        """
        if not value:
            return []

        # Already a list
        if isinstance(value, list):
            try:
                return [int(item) for item in value]
            except (ValueError, TypeError) as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_id_list_format",
                    translation_placeholders={"field": self.field_name},
                ) from err

        # Comma-separated string
        if isinstance(value, str):
            if "," in value:
                try:
                    return [int(s.strip()) for s in value.split(",") if s.strip()]
                except ValueError as err:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_id_format",
                        translation_placeholders={"field": self.field_name},
                    ) from err
            else:
                try:
                    return [int(value.strip())]
                except ValueError as err:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_id_format",
                        translation_placeholders={"field": self.field_name},
                    ) from err

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_field_type",
            translation_placeholders={
                "field": self.field_name,
                "expected_type": "list or comma-separated string",
                "type": type(value).__name__,
            },
        )


class CrewIDNormalizer(FieldNormalizer):
    """Normalize crew IDs from a list of strings or integers."""

    def normalize(self, value: str | list[str | int] | None) -> list[dict[str, int]]:
        """Extract crew IDs from entity IDs or direct crew IDs.

        Args:
            value: Entity ID(s) or crew ID(s)

        Returns:
            List of crew IDs as integers

        Raises:
            ServiceValidationError: If invalid format

        """
        if not value:
            return []

        crew_ids: list[dict[str, int]] = []

        # Normalize to list
        value_list = [value] if isinstance(value, str) else value

        for item in value_list:
            if isinstance(item, int):
                crew_ids.append({"id": item})
                continue

            if isinstance(item, str):
                item_str = item.strip()
                if not item_str:
                    continue

                try:
                    # Handle comma-separated strings
                    if "," in item_str:
                        for sub_item in item_str.split(","):
                            sub_item = sub_item.strip()
                            if sub_item:
                                crew_ids.append({"id": int(sub_item)})
                    else:
                        crew_ids.append({"id": int(item_str)})
                except ValueError as err:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_crew_id_format",
                        translation_placeholders={"crew_id": item_str},
                    ) from err

        return crew_ids


class StrListNormalizer(FieldNormalizer):
    """Normalize comma-separated strings or lists to list of strings."""

    def normalize(self, value: str | list[str] | None) -> list[str]:
        """Normalize to list of strings.

        Args:
            value: String, list, or None

        Returns:
            List of strings

        Raises:
            ServiceValidationError: If invalid format

        """
        if not value:
            return []

        # Already a list
        if isinstance(value, list):
            return [str(item) for item in value]

        # Comma-separated string
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_field_type",
            translation_placeholders={
                "field": self.field_name,
                "expected_type": "list or comma-separated string",
                "type": type(value).__name__,
            },
        )


class VehicleIdNormalizer(FieldNormalizer):
    """Normalize vehicle IDs from entity IDs or direct IDs."""

    def normalize(self, value: str | list[str | int] | None) -> list[int]:
        """Extract vehicle IDs from entity IDs or direct vehicle IDs.

        Args:
            value: Entity ID(s) or vehicle ID(s)

        Returns:
            List of vehicle IDs as integers

        Raises:
            ServiceValidationError: If invalid format

        """
        if not value:
            return []

        vehicle_ids: list[int] = []

        # Normalize to list
        values = [value] if isinstance(value, str) else value

        for item in values:
            item_str = str(item)

            # Handle comma-separated strings
            if "," in item_str:
                for sub_item in item_str.split(","):
                    sub_item = sub_item.strip()
                    if sub_item:
                        vehicle_ids.append(self._extract_vehicle_id(sub_item))
            else:
                vehicle_ids.append(self._extract_vehicle_id(item_str))

        return vehicle_ids

    def _extract_vehicle_id(self, value: str) -> int:
        """Extract vehicle ID from entity ID or direct ID.

        Args:
            value: Entity ID or vehicle ID as string

        Returns:
            Vehicle ID as integer

        Raises:
            ServiceValidationError: If extraction fails

        """
        try:
            # Entity ID format: "sensor.vehicle_123456"
            if "_" in value:
                return int(value.split("_")[-1])
            # Direct vehicle ID
            return int(value)
        except (ValueError, IndexError) as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_vehicle_id_format",
                translation_placeholders={"vehicle_id": value},
            ) from err


class DateTimeNormalizer(FieldNormalizer):
    """Normalize datetime strings to Unix timestamps."""

    def normalize(self, value: str | int | datetime | None) -> int | None:
        """Convert datetime to Unix timestamp.

        Args:
            value: Datetime as string, int timestamp, datetime object, or None

        Returns:
            Unix timestamp as integer or None

        Raises:
            ServiceValidationError: If invalid format

        """
        if not value:
            return None

        # Already a timestamp
        if isinstance(value, int):
            return value

        # Datetime object
        if isinstance(value, datetime):
            return int(value.timestamp())

        # Parse string
        if isinstance(value, str):
            try:
                # Check if it's already a Unix timestamp string
                if value.isdigit():
                    return int(value)

                # Parse ISO format or other datetime formats
                dt_obj = parse_datetime(value)
                if dt_obj is None:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_datetime_format",
                        translation_placeholders={"field": self.field_name},
                    )
                return int(dt_obj.timestamp())

            except (ValueError, TypeError, AttributeError) as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_datetime_format",
                    translation_placeholders={"field": self.field_name},
                ) from err

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_datetime_type",
            translation_placeholders={
                "field": self.field_name,
                "type": type(value).__name__,
            },
        )


class ServiceDataNormalizer:
    """Centralized service call data normalization."""

    def __init__(self) -> None:
        """Initialize normalizer with field-specific normalizers."""
        self._normalizers: dict[str, FieldNormalizer] = {
            "device_id": DeviceIdNormalizer("device_id"),
            # Integer list fields
            "group": IntListNormalizer("group"),
            "user_cluster_relation": IntListNormalizer("user_cluster_relation"),
            "vehicle": IntListNormalizer("vehicle"),
            "crew": IntListNormalizer("crew"),
            "answers": IntListNormalizer("answers"),
            "sorting": IntListNormalizer("sorting"),
            # String list fields
            "status": StrListNormalizer("status"),
            # Special fields
            "vehicle_id": VehicleIdNormalizer("vehicle_id"),
            # Datetime fields
            "ts_archive": DateTimeNormalizer("ts_archive"),
            "ts_publish": DateTimeNormalizer("ts_publish"),
            "newssurvey_ts_response": DateTimeNormalizer("newssurvey_ts_response"),
        }

    def normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize all fields in service call data.

        Args:
            data: Raw service call data

        Returns:
            Normalized data dictionary

        Raises:
            ServiceValidationError: If required fields missing or invalid format

        """
        normalized = data.copy()

        # Validate device_id is present (required for all services)
        if "device_id" not in normalized or not normalized["device_id"]:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_device_id",
            )

        # Apply field-specific normalizers
        for field_name, normalizer in self._normalizers.items():
            if field_name in normalized:
                normalized[field_name] = normalizer.normalize(normalized[field_name])

        return normalized


# Module-level instance for convenience
_normalizer = ServiceDataNormalizer()


def normalize_service_call_data(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize service call data from various sources.

    This is needed as device_actions, frontend actions and developer tools have different formats.

    Handles inconsistencies between:
    - Developer Tools (lists for targets)
    - Device Actions (strings for targets)
    - Different formats for ID lists

    Args:
        data: Raw service call data

    Returns:
        Normalized data dictionary with consistent types

    Raises:
        ServiceValidationError: If data format is invalid

    """
    return _normalizer.normalize(data)
