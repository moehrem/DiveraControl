"""Error handling classes."""

import logging

_LOGGER = logging.getLogger(__name__)


class DiveraAPIError(Exception):
    """Handles authentication api errors."""

    def __init__(self, error: str) -> None:
        """Initialize DiveraAPIError."""
        super().__init__(error)
        _LOGGER.error("Authentifizierung bei Divera fehlgeschlagen: %s", str(error))


class DiveraSetupError(Exception):
    """Error in config flow, raised for.

    Raised in:
    - new setup
    - reconfigure.

    """

    def __init__(self, error: str) -> None:
        """Initialize DiveraSetupError."""
        super().__init__(error)
        _LOGGER.error("")
