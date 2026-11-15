"""Live integration tests for object details."""

import pytest

from metmuseum.models import Artwork

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("object_id", [436524, 45734])
def test_get_existing_artwork(api_client, object_id):
    """An existing artwork must have a valid HTTP response and schema."""
    response = api_client.artwork(object_id)
    assert response.status_code == 200

    artwork = Artwork.model_validate(response.json())
    assert artwork.object_id == object_id
    assert artwork.title.strip()
    assert artwork.department.strip()
    assert artwork.begin_date <= artwork.end_date


def test_get_nonexistent_artwork(api_client):
    """An unknown object ID must yield 404 with an error message."""
    response = api_client.artwork(999_999_999)
    assert response.status_code == 404

    body = response.json()
    assert isinstance(body, dict)
    assert isinstance(body.get("message"), str)
