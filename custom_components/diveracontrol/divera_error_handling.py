"""Therein all error handling classes."""

import logging

_LOGGER = logging.getLogger(__name__)


class DiveraAPIError(Exception):
    """Fehler für Authentifizierungsprobleme bei Divera."""

    def __init__(self, error: str) -> None:
        """Initialisiert den Fehler."""
        super().__init__(error)
        _LOGGER.error("Authentifizierung bei Divera fehlgeschlagen: %s", str(error))


class DiveraSetupError(Exception):
    """Error in config flow: new setup, reconfigure."""

    def __init__(self, error: str) -> None:
        """Initialize DiveraSetupError."""
        super().__init__(error)
        _LOGGER.error("")
