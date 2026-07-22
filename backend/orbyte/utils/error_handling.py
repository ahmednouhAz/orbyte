"""
Standardized error handling utilities.
"""

from orbyte.configs.app_configs import CONTINUE_ON_CONNECTOR_FAILURE
from orbyte.utils.logger import setup_logger

logger = setup_logger()


def handle_connector_error(e: Exception, context: str) -> None:
    """
    Standard error handling for connectors.

    Args:
        e: The exception that was raised
        context: A description of where the error occurred

    Raises:
        The original exception if CONTINUE_ON_CONNECTOR_FAILURE is False
    """
    logger.error("Error in %s: %s", context, e, exc_info=e)
    if not CONTINUE_ON_CONNECTOR_FAILURE:
        raise
