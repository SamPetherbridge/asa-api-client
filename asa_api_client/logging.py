"""Logging configuration for the Apple Search Ads API client.

This module provides a configurable logging setup that allows users
to control the verbosity and format of log output from the library.

Example:
    Configure logging at application startup::

        from asa_api_client import configure_logging
        import logging

        # Enable debug logging
        configure_logging(level=logging.DEBUG)

        # Or configure with custom handler
        handler = logging.FileHandler("asa_api.log")
        configure_logging(level=logging.INFO, handler=handler)

    Disable library logging::

        configure_logging(level=logging.CRITICAL)
"""

import logging
import sys
from typing import TextIO

# Library logger - all library modules should use this
logger = logging.getLogger("asa_api")

# Default to NullHandler to avoid "No handler found" warnings
# Users must explicitly configure logging to see output
logger.addHandler(logging.NullHandler())


def configure_logging(
    *,
    level: int = logging.INFO,
    handler: logging.Handler | None = None,
    format_string: str | None = None,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure logging for the asa_api library.

    This function sets up logging for all library components. Call it
    once at application startup to enable log output.

    Args:
        level: The logging level (e.g., logging.DEBUG, logging.INFO).
            Defaults to INFO.
        handler: A custom logging handler. If not provided, a
            StreamHandler will be created.
        format_string: Custom format string for log messages. If not
            provided, a sensible default is used.
        stream: Output stream for the default StreamHandler. Defaults
            to sys.stderr. Ignored if a custom handler is provided.

    Returns:
        The configured logger instance.

    Example:
        Basic configuration::

            from asa_api_client import configure_logging
            import logging

            configure_logging(level=logging.DEBUG)

        Custom format::

            configure_logging(
                level=logging.INFO,
                format_string="%(asctime)s - %(name)s - %(message)s"
            )

        File logging::

            handler = logging.FileHandler("api.log")
            configure_logging(level=logging.DEBUG, handler=handler)
    """
    # Remove existing handlers
    logger.handlers.clear()

    # Set the logging level
    logger.setLevel(level)

    # Create handler if not provided
    if handler is None:
        handler = logging.StreamHandler(stream or sys.stderr)

    # Set format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    # Add the handler
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module.

    This creates a child logger under the main 'asa_api' logger,
    which inherits the parent's configuration.

    Args:
        name: The name for the child logger, typically __name__.

    Returns:
        A child logger instance.

    Example:
        In a module::

            from asa_api_client.logging import get_logger

            logger = get_logger(__name__)
            logger.debug("Processing request")
    """
    return logger.getChild(name)
