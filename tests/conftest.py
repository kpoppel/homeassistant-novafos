import pytest
from custom_components.novafos import Novafos
import json
import logging
import sys

# import datetime
# from typing import Final, Generator
# from unittest.mock import MagicMock

# import pytest
# from pytest_mock import MockFixture

# # Mocking the datetime-now() function to match test data
# DEC_29: Final[datetime.datetime] = datetime.datetime(2024, 12, 29, 0, 0, 0)

# @pytest.fixture
# def datetime_fixture(mocker: MockFixture) -> Generator[MagicMock, None, None]:
#     """ Fixture to mock datetime.now() to always give out the same point in time. """
#     mocked_datetime = mocker.patch(
#         "custom_components.novafos.Novafos.datetime.datetime",
#     )
#     mocked_datetime.datetime.now.return_value = DEC_29
#     yield mocked_datetime

# @pytest.fixture(autouse=True)
# def auto_enable_custom_integrations(enable_custom_integrations):
#     """Enable custom integrations."""
#     return

# ---

@pytest.fixture(scope="module")
def novafos():
    """Fixture to provide a single instance of Novafos for all tests in the module."""
    print("Setting up Novafos instance")
    instance = Novafos()  
    yield instance  # Yield instance to the tests
    print("\nTearing down Novafos instance")

@pytest.fixture(autouse=True)  # Apply to all tests automatically
def configure_logging(caplog):
    caplog.set_level(logging.DEBUG) # Default log level for tests
    # You can add more logging configuration here if needed

@pytest.fixture(autouse=True, scope="session")
def configure_logging():
    """Configures root logger to output to stdout."""
    root_logger = logging.getLogger()

    if root_logger.hasHandlers(): # Prevent adding multiple handlers
        return

    root_logger.setLevel(logging.DEBUG)  # Set the desired root logging level

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
