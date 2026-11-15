"""Offline tests for Pydantic validation and logging."""

import logging
from unittest.mock import Mock

import pytest
import requests
from pydantic import ValidationError

from metmuseum.client import MetMuseumClient, SearchParameters
from metmuseum.models import Artwork, SearchResults


@pytest.fixture
def artwork_data():
    """Minimal valid artwork data in the real API format."""
    return {
        "objectID": 436524,
        "title": "Sunflowers",
        "artistDisplayName": "Vincent van Gogh",
        "objectDate": "1887",
        "objectBeginDate": 1887,
        "objectEndDate": 1887,
        "department": "European Paintings",
        "objectName": "Painting",
        "medium": "Oil on canvas",
        "isHighlight": True,
        "isPublicDomain": True,
        "primaryImage": "https://example.org/painting.jpg",
        "primaryImageSmall": "https://example.org/small.jpg",
        "additionalImages": [],
        "tags": [{"term": "Flowers"}],
        "constituents": None,
        "extraApiProperty": "allowed",
    }


def test_artwork_schema(artwork_data):
    """CamelCase API fields map to idiomatic Python attributes."""
    artwork = Artwork.model_validate(artwork_data)
    assert artwork.object_id == 436524
    assert artwork.artist_name == "Vincent van Gogh"
    assert artwork.tags[0].term == "Flowers"


def test_artwork_missing_field(artwork_data):
    """An object without its required ID is invalid."""
    del artwork_data["objectID"]
    with pytest.raises(ValidationError):
        Artwork.model_validate(artwork_data)


def test_artwork_wrong_type(artwork_data):
    """String IDs should not pass strict integer validation."""
    artwork_data["objectID"] = "436524"
    with pytest.raises(ValidationError):
        Artwork.model_validate(artwork_data)


def test_artwork_invalid_dates(artwork_data):
    """Creation date must not begin after it ends."""
    artwork_data["objectBeginDate"] = 1900
    with pytest.raises(ValidationError):
        Artwork.model_validate(artwork_data)


@pytest.mark.parametrize("ids", [None, []])
def test_empty_search_schema(ids):
    """The API can encode an empty result page two ways."""
    result = SearchResults.model_validate({"total": 0, "objectIDs": ids})
    assert result.object_ids in (None, [])


def test_duplicate_ids_are_invalid():
    """The same ID cannot occur twice in a single page."""
    with pytest.raises(ValidationError):
        SearchResults.model_validate(
            {"total": 5, "objectIDs": [101, 101]}
        )


@pytest.mark.parametrize(
    "filters",
    [
        {"date_begin": 1800},
        {"date_begin": 1900, "date_end": 1800},
        {"offset": -1},
        {"limit": 0},
        {"offset": 9999, "limit": 5},
    ],
)
def test_invalid_search_parameters(filters):
    """Reject invalid date and pagination options before HTTP."""
    with pytest.raises(ValidationError):
        SearchParameters.model_validate(filters)


def test_query_serialization():
    """Serialize API aliases and lowercase boolean values."""
    parameters = SearchParameters(
        query="flowers",
        has_images=True,
        department_id=11,
        limit=5,
    )
    assert parameters.to_query() == {
        "q": "flowers",
        "offset": 0,
        "limit": 5,
        "departmentId": 11,
        "hasImages": "true",
    }


def test_logs_successful_http(caplog):
    """Log requests, response statuses and response bodies."""
    response = Mock(status_code=200, url="https://example.org/test")
    response.text = '{"total":0,"objectIDs":null}'
    session = Mock()
    session.get.return_value = response
    client = MetMuseumClient(session=session)

    with caplog.at_level(logging.INFO):
        actual = client.search(query="sunflowers", limit=5)

    assert actual is response
    assert "Request: GET" in caplog.text
    assert "Response: status=200" in caplog.text
    args, kwargs = session.get.call_args
    assert args[0].endswith("/v1.1/search")
    assert kwargs["params"]["q"] == "sunflowers"


def test_logs_http_error(caplog):
    """HTTP 404 is logged as an error."""
    response = Mock(status_code=404, url="https://example.org/missing")
    response.text = '{"message":"ObjectID not found"}'
    session = Mock()
    session.get.return_value = response
    client = MetMuseumClient(session=session)

    with caplog.at_level(logging.ERROR):
        assert client.artwork(999999999).status_code == 404

    assert "HTTP error: status=404" in caplog.text


def test_logs_network_exception(caplog):
    """A network error is logged and passed through to pytest."""
    session = Mock()
    session.get.side_effect = requests.Timeout("No response")
    client = MetMuseumClient(session=session)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.Timeout):
            client.artwork(436524)

    assert "Request failed" in caplog.text
