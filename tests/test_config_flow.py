"""Tests for DiveraControl config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.config_flow import (
    ABORT_REASON_ALREADY_CONFIGURED,
    ABORT_REASON_MERGE_SUCCESS,
    ABORT_REASON_NO_HUBS,
    ABORT_REASON_UNKNOWN_STEP,
    DiveraControlConfigFlow,
    ERROR_API_KEY,
    ERROR_LOGIN,
    STEP_API_KEY,
    STEP_LOGIN,
    STEP_MULTI_CLUSTER,
    STEP_USER,
)


class TestConfigFlowInitialization:
    """Test config flow initialization."""

    def test_config_flow_init(self, hass: HomeAssistant) -> None:
        """Test config flow initialization."""
        flow = DiveraControlConfigFlow()
        flow.hass = hass
        assert flow.final_entry is None
        assert flow.possible_entries == {}
        assert flow.errors == {}

    def test_form_handlers_defined(self) -> None:
        """Test that form handlers are defined."""
        assert DiveraControlConfigFlow.FORM_HANDLERS is not None
        assert len(DiveraControlConfigFlow.FORM_HANDLERS) > 0


class TestConfigFlowStepUser:
    """Test async_step_user method."""

    @pytest.mark.asyncio
    async def test_async_step_user_forwards_to_login(self, hass: HomeAssistant) -> None:
        """Test that step_user forwards to step_login."""
        flow = DiveraControlConfigFlow()
        flow.hass = hass

        with patch.object(
            flow, "async_step_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = {"type": "form", "step_id": "login"}
            result = await flow.async_step_user(None)
            mock_login.assert_called_once_with(None)


class TestConfigFlowConstants:
    """Test config flow constants."""

    def test_abort_reasons_defined(self) -> None:
        """Test that abort reasons are defined."""
        assert ABORT_REASON_NO_HUBS == "no_new_hubs_found"
        assert ABORT_REASON_ALREADY_CONFIGURED == "already_configured"
        assert ABORT_REASON_MERGE_SUCCESS == "merge_successful"
        assert ABORT_REASON_UNKNOWN_STEP == "unknown_step"

    def test_error_codes_defined(self) -> None:
        """Test that error codes are defined."""
        assert ERROR_API_KEY == "api_key_error"
        assert ERROR_LOGIN == "login_error"

    def test_step_constants_defined(self) -> None:
        """Test that step constants are defined."""
        assert STEP_USER == "user"
        assert STEP_LOGIN == "login"
        assert STEP_API_KEY == "accesskey"
        assert STEP_MULTI_CLUSTER == "multi_cluster"
