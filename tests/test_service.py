"""Tests for the DiveraControl service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.diveracontrol.const import DOMAIN
from custom_components.diveracontrol.service import (
    POST_ALARM_VALIDATION_RULES,
    POST_USING_VEHICLE_CREW_VALIDATION_RULES,
    POST_VEHICLE_VALIDATION_RULES,
    _build_payload,
    _extract_news,
    _extract_survey,
    _validate_data,
    async_register_services,
    handle_post_alarm,
    handle_post_close_alarm,
    handle_post_message,
    handle_post_news,
    handle_post_using_vehicle_crew,
    handle_post_using_vehicle_property,
    handle_post_vehicle_status,
    handle_put_alarm,
)


class TestValidateData:
    """Test validation function."""

    def test_validate_data_success(self):
        """Test successful validation."""
        data = {"vehicle_id": [123]}
        # Should not raise any exception
        _validate_data(data, POST_VEHICLE_VALIDATION_RULES)

    def test_validate_data_failure_no_vehicle_id(self):
        """Test validation failure for missing vehicle_id."""
        data = {}
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_data(data, POST_VEHICLE_VALIDATION_RULES)

        assert exc_info.value.translation_key == "no_vehicle_id"
        assert exc_info.value.translation_domain == DOMAIN

    def test_validate_data_failure_no_alarm_title(self):
        """Test validation failure for missing alarm title."""
        data = {"notification_type": 1}
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_data(data, POST_ALARM_VALIDATION_RULES)

        assert exc_info.value.translation_key == "no_alarm_title"

    def test_validate_data_failure_with_callable_placeholders(self):
        """Test validation failure with callable translation placeholders."""
        data = {"vehicle_id": [123, 456], "mode": "add"}
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_data(data, POST_USING_VEHICLE_CREW_VALIDATION_RULES)

        # Should fail on vehicle_count validation
        assert exc_info.value.translation_key == "invalid_number_of_vehicles"
        assert exc_info.value.translation_placeholders == {"num_vehicles": "2"}


class TestBuildPayload:
    """Test payload building function."""

    def test_build_payload_flat(self):
        """Test building flat payload without keys."""
        data = {
            "vehicle_id": 123,
            "fmsstatus": 2,
            "device_id": "test_device",
            "cluster_id": "test_cluster",
            "extra": "value",
        }
        payload = _build_payload(data, keys=None)

        assert payload == {"vehicle_id": 123, "fmsstatus": 2, "extra": "value"}
        assert "device_id" not in payload
        assert "cluster_id" not in payload

    def test_build_payload_with_single_key(self):
        """Test building payload with single key."""
        data = {"title": "Test Alarm", "notification_type": 3, "device_id": "test"}
        payload = _build_payload(data, keys={"Alarm": {}})

        assert "Alarm" in payload
        assert payload["Alarm"] == {"title": "Test Alarm", "notification_type": 3}

    def test_build_payload_with_multiple_keys(self):
        """Test building payload with multiple keys."""
        data = {"title": "News", "text": "Content"}
        survey_data = {"answers": ["Yes", "No"], "sorting": "abc"}
        payload = _build_payload(data, keys={"News": {}, "newssurvey": survey_data})

        assert "News" in payload
        assert "newssurvey" in payload
        assert payload["newssurvey"] == survey_data

    def test_build_payload_with_specific_data(self):
        """Test building payload with specific data in keys."""
        data = {"text": "Test message"}
        payload = _build_payload(
            data, keys={"Message": {"message_channel_id": 456, "text": "Test message"}}
        )

        assert payload == {
            "Message": {"message_channel_id": 456, "text": "Test message"}
        }

    def test_build_payload_exclude_keys(self):
        """Test building payload with excluded keys."""
        data = {
            "title": "Test",
            "newssurvey_answers": "data",
            "newssurvey_sorting": "abc",
            "vehicle_id": 123,
        }
        exclude = {k for k in data if k.startswith("newssurvey_")}
        payload = _build_payload(data, keys={"News": {}}, exclude_keys=exclude)

        # Only device_id and cluster_id are excluded by default, not vehicle_id
        assert payload["News"] == {"title": "Test", "vehicle_id": 123}
        assert "newssurvey_answers" not in payload["News"]
        assert "newssurvey_sorting" not in payload["News"]

    def test_build_payload_none_values_excluded(self):
        """Test that None values are excluded from payload."""
        data = {"title": "Test", "description": None, "priority": 1}
        payload = _build_payload(data, keys=None)

        assert "description" not in payload
        assert payload == {"title": "Test", "priority": 1}


class TestExtractFunctions:
    """Test data extraction functions."""

    def test_extract_news(self):
        """Test extracting news data."""
        data = {
            "title": "Important News",
            "text": "Content",
            "newssurvey_answers": ["Yes", "No"],
            "newssurvey_sorting": "abc",
        }
        news_data = _extract_news(data, notification_type=3)

        assert news_data == {"title": "Important News", "text": "Content"}
        assert "newssurvey_answers" not in news_data

    def test_extract_survey(self):
        """Test extracting survey data."""
        data = {
            "title": "News",
            "newssurvey_answers": ["Yes", "No"],
            "newssurvey_sorting": "abc",
            "newssurvey_title": "Survey",
        }
        survey_data = _extract_survey(data)

        # newssurvey_title becomes "title" in survey_data (prefix is stripped)
        assert survey_data == {
            "answers": ["Yes", "No"],
            "sorting": "abc",
            "title": "Survey",
        }


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def mock_api_instance():
    """Create a mock API instance."""
    api = AsyncMock()
    api.ucr_id = "test_cluster"
    api.post_vehicle_status = AsyncMock()
    api.post_alarms = AsyncMock()
    api.put_alarms = AsyncMock()
    api.post_close_alarm = AsyncMock()
    api.post_message = AsyncMock()
    api.post_using_vehicle_property = AsyncMock()
    api.post_using_vehicle_crew = AsyncMock()
    api.post_news = AsyncMock()
    return api


@pytest.fixture
def mock_service_call():
    """Create a mock ServiceCall."""
    call = MagicMock(spec=ServiceCall)
    call.service = "test_service"
    call.data = {}
    return call


class TestHandlePostVehicleStatus:
    """Test handle_post_vehicle_status handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_success(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful vehicle status update."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "fmsstatus": 2,
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_post_vehicle_status(mock_hass, mock_service_call)

        # Payload includes vehicle_id since no keys are specified in _build_payload
        mock_api_instance.post_vehicle_status.assert_called_once_with(
            123, {"vehicle_id": [123], "fmsstatus": 2}
        )
        mock_handle_entity.assert_called_once()

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.get_translation")
    async def test_api_error(
        self,
        mock_translation,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test handling of API error."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "fmsstatus": 2,
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_api_instance.post_vehicle_status.side_effect = HomeAssistantError(
            "API Error"
        )
        mock_translation.return_value = "Error message"

        # Should not raise, just log
        await handle_post_vehicle_status(mock_hass, mock_service_call)

        mock_translation.assert_called_once()

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    async def test_validation_error(self, mock_normalize, mock_hass, mock_service_call):
        """Test validation error for missing vehicle_id."""
        mock_normalize.return_value = {"device_id": "test_device"}

        with pytest.raises(ServiceValidationError):
            await handle_post_vehicle_status(mock_hass, mock_service_call)


class TestHandlePostAlarm:
    """Test handle_post_alarm handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_success(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful alarm creation."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "title": "Fire Alert",
            "notification_type": 3,
        }
        mock_get_coordinator.return_value = mock_api_instance

        await handle_post_alarm(mock_hass, mock_service_call)

        mock_api_instance.post_alarms.assert_called_once()
        call_args = mock_api_instance.post_alarms.call_args[0][0]
        assert "Alarm" in call_args
        assert call_args["Alarm"]["title"] == "Fire Alert"

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.get_translation")
    async def test_api_error(
        self,
        mock_translation,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test handling of API error."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "title": "Fire Alert",
            "notification_type": 3,
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_api_instance.post_alarms.side_effect = HomeAssistantError("API Error")
        mock_translation.return_value = "Error message"

        await handle_post_alarm(mock_hass, mock_service_call)

        mock_translation.assert_called_once()


class TestHandlePutAlarm:
    """Test handle_put_alarm handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_success(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful alarm update."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "alarm_id": 789,
            "title": "Updated Alert",
            "notification_type": 3,
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_put_alarm(mock_hass, mock_service_call)

        mock_api_instance.put_alarms.assert_called_once()
        call_args = mock_api_instance.put_alarms.call_args
        assert call_args[0][0] == 789  # alarm_id
        assert "Alarm" in call_args[0][1]


class TestHandlePostCloseAlarm:
    """Test handle_post_close_alarm handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_success(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful alarm closing."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "alarm_id": 789,
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_post_close_alarm(mock_hass, mock_service_call)

        mock_api_instance.post_close_alarm.assert_called_once()
        call_args = mock_api_instance.post_close_alarm.call_args
        assert call_args[0][1] == 789  # alarm_id as second argument


class TestHandlePostMessage:
    """Test handle_post_message handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_success_with_message_channel_id(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful message posting with direct message_channel_id."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "message_channel_id": 456,
            "text": "Test message",
        }
        mock_get_coordinator.return_value = mock_api_instance

        await handle_post_message(mock_hass, mock_service_call)

        mock_api_instance.post_message.assert_called_once()
        call_args = mock_api_instance.post_message.call_args[0][0]
        assert "Message" in call_args
        assert call_args["Message"]["message_channel_id"] == 456

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_success_with_alarm_id(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful message posting using alarm_id to find channel."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "alarm_id": 789,
            "text": "Test message",
        }
        mock_coord_data = MagicMock()
        mock_coord_data.get.return_value = {"items": {789: {"message_channel_id": 999}}}
        mock_get_coordinator.side_effect = [mock_coord_data, mock_api_instance]

        await handle_post_message(mock_hass, mock_service_call)

        mock_api_instance.post_message.assert_called_once()
        call_args = mock_api_instance.post_message.call_args[0][0]
        assert call_args["Message"]["message_channel_id"] == 999

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_no_message_channel_found(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_service_call,
    ):
        """Test error when no message channel can be determined."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "alarm_id": 789,
            "text": "Test message",
        }
        mock_coord_data = MagicMock()
        mock_coord_data.get.return_value = {"items": {}}
        mock_get_coordinator.return_value = mock_coord_data

        with pytest.raises(ServiceValidationError) as exc_info:
            await handle_post_message(mock_hass, mock_service_call)

        assert exc_info.value.translation_key == "no_message_channel"


class TestHandlePostUsingVehicleProperty:
    """Test handle_post_using_vehicle_property handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_success(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful vehicle property update."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "property1": "value1",
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_post_using_vehicle_property(mock_hass, mock_service_call)

        mock_api_instance.post_using_vehicle_property.assert_called_once_with(
            123, {"property1": "value1"}
        )


class TestHandlePostUsingVehicleCrew:
    """Test handle_post_using_vehicle_crew handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_add_crew(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test adding crew members."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "mode": "add",
            "crew": [456, 789],
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_post_using_vehicle_crew(mock_hass, mock_service_call)

        call_args = mock_api_instance.post_using_vehicle_crew.call_args
        assert call_args[0][0] == 123  # vehicle_id
        assert call_args[0][1] == "add"  # mode
        assert "Crew" in call_args[0][2]
        assert call_args[0][2]["Crew"]["add"] == [456, 789]

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_remove_crew(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test removing crew members."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "mode": "remove",
            "crew": [456],
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_post_using_vehicle_crew(mock_hass, mock_service_call)

        call_args = mock_api_instance.post_using_vehicle_crew.call_args
        assert call_args[0][2]["Crew"]["remove"] == [456]

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    @patch("custom_components.diveracontrol.service.handle_entity")
    async def test_reset_crew(
        self,
        mock_handle_entity,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test resetting crew."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "mode": "reset",
        }
        mock_get_coordinator.return_value = mock_api_instance
        mock_handle_entity.return_value = None

        await handle_post_using_vehicle_crew(mock_hass, mock_service_call)

        call_args = mock_api_instance.post_using_vehicle_crew.call_args
        assert call_args[0][2] == {}  # Empty payload for reset

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_invalid_mode(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test invalid crew mode."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "vehicle_id": [123],
            "mode": "invalid",
        }
        mock_get_coordinator.return_value = mock_api_instance

        with pytest.raises(ServiceValidationError) as exc_info:
            await handle_post_using_vehicle_crew(mock_hass, mock_service_call)

        assert exc_info.value.translation_key == "invalid_mode"


class TestHandlePostNews:
    """Test handle_post_news handler."""

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_success_without_survey(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful news posting without survey."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "title": "Important News",
            "notification_type": 3,
            "text": "News content",
            "group": [1, 2],  # Required for notification_type 3
        }
        mock_get_coordinator.return_value = mock_api_instance

        await handle_post_news(mock_hass, mock_service_call)

        mock_api_instance.post_news.assert_called_once()
        call_args = mock_api_instance.post_news.call_args[0][0]
        assert "News" in call_args
        assert call_args["News"]["title"] == "Important News"

    @patch("custom_components.diveracontrol.service.normalize_service_call_data")
    @patch("custom_components.diveracontrol.service.get_coordinator_key_from_device")
    async def test_success_with_survey(
        self,
        mock_get_coordinator,
        mock_normalize,
        mock_hass,
        mock_api_instance,
        mock_service_call,
    ):
        """Test successful news posting with survey."""
        mock_normalize.return_value = {
            "device_id": "test_device",
            "title": "Survey News",
            "notification_type": 3,
            "survey": True,
            "newssurvey_answers": ["Yes", "No"],
            "newssurvey_sorting": "abc",
            "group": [1, 2],  # Required for notification_type 3
        }
        mock_get_coordinator.return_value = mock_api_instance

        await handle_post_news(mock_hass, mock_service_call)

        call_args = mock_api_instance.post_news.call_args[0][0]
        assert "News" in call_args
        assert "newssurvey" in call_args
        assert call_args["newssurvey"]["answers"] == ["Yes", "No"]


class TestAsyncRegisterServices:
    """Test service registration."""

    def test_register_all_services(self, mock_hass):
        """Test that all services are registered."""
        # Setup services mock
        mock_hass.services = MagicMock()
        mock_hass.services.async_register = MagicMock()

        async_register_services(mock_hass, DOMAIN)

        # Verify all 8 services were registered
        assert mock_hass.services.async_register.call_count == 8

        # Verify service names
        registered_services = [
            call[0][1] for call in mock_hass.services.async_register.call_args_list
        ]
        expected_services = [
            "post_vehicle_status",
            "post_alarm",
            "put_alarm",
            "post_close_alarm",
            "post_message",
            "post_using_vehicle_property",
            "post_using_vehicle_crew",
            "post_news",
        ]
        for service in expected_services:
            assert service in registered_services
