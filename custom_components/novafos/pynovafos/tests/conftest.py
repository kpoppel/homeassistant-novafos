import pytest
from novafos import Novafos
import json
import logging
import sys

@pytest.fixture(scope="module")
def novafos():
    """Fixture to provide a single instance of Novafos for all tests in the module."""
    print("Setting up Novafos instance")
    with open('tests/novafos_test.config', 'r') as f:
        config = json.load(f)
    instance = Novafos(username=config['username'], password=config['password'], supplierid=config['supplierid'])  
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
