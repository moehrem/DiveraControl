"""In-memory log handler for DiveraControl diagnostics."""

from collections import deque
import logging

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER_NAME = f"custom_components.{DOMAIN}"
_LOGS_KEY = f"{DOMAIN}_logs_handler"
_MAX_RECORDS = 500


class DiveraControlLogHandler(logging.Handler):
    """Log handler that stores recent records in memory."""

    def __init__(self) -> None:
        """Initialize the log handler with a fixed-size deque."""
        super().__init__()
        self._records: deque[logging.LogRecord] = deque(maxlen=_MAX_RECORDS)

    def emit(self, record: logging.LogRecord) -> None:
        """Store a log record in the ring buffer."""
        self._records.append(record)

    async def async_get_logs(self, hass: HomeAssistant) -> list[str]:
        """Return formatted logs from memory."""

        def _format_logs() -> list[str]:
            records = self._records.copy()
            return [self.format(record) for record in records]

        return await hass.async_add_executor_job(_format_logs)


# create a single instance of the handler to be shared across the integration
_handler = DiveraControlLogHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s (%(name)s) %(message)s")
)
logging.getLogger(_LOGGER_NAME).addHandler(_handler)


def async_setup_diveracontrol_log_handler(hass: HomeAssistant) -> None:
    """Store the handler in hass.data for later access."""
    if _LOGS_KEY in hass.data:
        return
    hass.data[_LOGS_KEY] = _handler


def async_remove_diveracontrol_log_handler(hass: HomeAssistant) -> None:
    """Remove the handler reference from hass.data."""
    hass.data.pop(_LOGS_KEY, None)


async def async_get_diveracontrol_logs(hass: HomeAssistant) -> list[str]:
    """Return recent logs from the in-memory log handler."""
    handler = hass.data.get(_LOGS_KEY) or _handler
    return await handler.async_get_logs(hass)
