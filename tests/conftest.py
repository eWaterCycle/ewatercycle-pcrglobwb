import pytest

from ewatercycle.testing import rhine_shape


@pytest.fixture
def sample_shape():
    """Return the path to the Rhine shapefile bundled with ewatercycle."""
    return str(rhine_shape())
