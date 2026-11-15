"""Reusable pytest fixtures for live API calls."""

import pytest

from metmuseum.client import MetMuseumClient


@pytest.fixture(scope="session")
def api_client():
    """Reuse a single HTTP session for integration tests."""
    client = MetMuseumClient()
    yield client
    client.close()
