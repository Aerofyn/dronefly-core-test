"""Test INatAPI."""
import pytest
from dronefly.core.apis.inat import INatAPI

# pylint: disable=missing-function-docstring


@pytest.fixture(name="inat_api")
async def fixture_inat_api():
    return INatAPI()
