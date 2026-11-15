"""Live tests of search, pagination, limits and filters."""

import pytest

from metmuseum.models import Artwork, SearchResults

pytestmark = pytest.mark.integration


def search_results(api_client, **parameters):
    """Validate the HTTP status and Pydantic response schema."""
    response = api_client.search(**parameters)
    assert response.status_code == 200
    return SearchResults.model_validate(response.json())


def test_search_by_keyword(api_client):
    """Searching a known keyword should yield object IDs."""
    result = search_results(api_client, query="sunflowers", limit=10)
    assert result.total > 0
    assert result.object_ids
    assert 0 < len(result.object_ids) <= 10


def test_search_without_matches(api_client):
    """Empty results may use null or an empty list for objectIDs."""
    result = search_results(
        api_client,
        query="zzzx_no_such_artwork_29571942_zzzx",
        limit=5,
    )
    assert result.total == 0
    assert result.object_ids in (None, [])


def test_default_page_limit(api_client):
    """The default search page has up to 100 results."""
    result = search_results(api_client, query="cat")
    assert result.total > 100
    assert result.object_ids is not None
    assert len(result.object_ids) == 100


@pytest.mark.parametrize("limit", [1, 5, 20])
def test_requested_page_limit(api_client, limit):
    """An explicit limit is respected by the search API."""
    result = search_results(api_client, query="cat", limit=limit)
    assert result.total >= limit
    assert result.object_ids is not None
    assert len(result.object_ids) == limit


def test_maximum_page_limit(api_client):
    """The API caps an overly large requested limit at 500."""
    result = search_results(api_client, query="cat", limit=600)
    assert result.total > 500
    assert result.object_ids is not None
    assert len(result.object_ids) == 500


def test_pagination_has_no_duplicate_pages(api_client):
    """Adjacent pages should have distinct object IDs."""
    first = search_results(api_client, query="cat", offset=0, limit=5)
    second = search_results(api_client, query="cat", offset=5, limit=5)
    assert first.total == second.total
    assert first.object_ids and second.object_ids
    assert set(first.object_ids).isdisjoint(second.object_ids)


def test_filter_by_department(api_client):
    """Works in department 11 belong to European Paintings."""
    result = search_results(
        api_client,
        query="sunflowers",
        department_id=11,
        limit=5,
    )
    assert result.total > 0
    assert result.object_ids

    response = api_client.artwork(result.object_ids[0])
    assert response.status_code == 200
    artwork = Artwork.model_validate(response.json())
    assert artwork.department == "European Paintings"


def test_filter_highlights(api_client):
    """The highlight filter returns highlighted objects."""
    result = search_results(
        api_client,
        query="sunflowers",
        is_highlight=True,
        limit=5,
    )
    assert result.total > 0
    assert result.object_ids

    response = api_client.artwork(result.object_ids[0])
    assert response.status_code == 200
    artwork = Artwork.model_validate(response.json())
    assert artwork.is_highlight is True


def test_filter_by_date(api_client):
    """Works selected by date must overlap the requested period."""
    result = search_results(
        api_client,
        query="sunflowers",
        date_begin=1800,
        date_end=1900,
        limit=5,
    )
    assert result.total > 0
    assert result.object_ids

    response = api_client.artwork(result.object_ids[0])
    assert response.status_code == 200
    artwork = Artwork.model_validate(response.json())
    assert artwork.begin_date <= 1900
    assert artwork.end_date >= 1800
