"""Configuration for pytest."""
from pytest import Function


def pytest_collection_modifyitems(config, items):
    """Disable test execution if -p no:unittest is defined."""
    plugins = config.getoption('plugins', default=None)
    if plugins and 'no:unittest' in plugins:
        for item in reversed(items):
            if isinstance(item, Function):
                items.remove(item)
