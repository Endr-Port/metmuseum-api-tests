"""Met Museum HTTP client with logging and validated search parameters."""

import logging
from time import perf_counter
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field, model_validator
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://collectionapi.metmuseum.org/public/collection"


class SearchParameters(BaseModel):
    """API search parameters with Python-friendly attribute names."""

    model_config = ConfigDict(strict=True, populate_by_name=True)

    query: str | None = Field(default=None, alias="q")
    offset: int = Field(default=0, ge=0)
    limit: int | None = Field(default=None, ge=1)
    is_highlight: bool | None = Field(default=None, alias="isHighlight")
    title_only: bool | None = Field(default=None, alias="title")
    tags_only: bool | None = Field(default=None, alias="tags")
    department_id: int | None = Field(default=None, alias="departmentId")
    is_on_view: bool | None = Field(default=None, alias="isOnView")
    artist_or_culture: bool | None = Field(
        default=None, alias="artistOrCulture"
    )
    medium: str | None = None
    has_images: bool | None = Field(default=None, alias="hasImages")
    geo_location: str | None = Field(default=None, alias="geoLocation")
    date_begin: int | None = Field(default=None, alias="dateBegin")
    date_end: int | None = Field(default=None, alias="dateEnd")

    @model_validator(mode="after")
    def validate_range(self) -> "SearchParameters":
        """Enforce documented date and pagination constraints."""
        if (self.date_begin is None) != (self.date_end is None):
            raise ValueError("dateBegin and dateEnd must be paired")
        if (
            self.date_begin is not None
            and self.date_end is not None
            and self.date_begin > self.date_end
        ):
            raise ValueError("dateBegin exceeds dateEnd")
        if self.limit is not None and self.offset + self.limit > 10_000:
            raise ValueError("offset + limit exceeds 10000")
        return self

    def to_query(self) -> dict[str, Any]:
        """Convert booleans to lowercase HTTP query values."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        return {
            key: str(value).lower() if isinstance(value, bool) else value
            for key, value in data.items()
        }


class MetMuseumClient:
    """Object calls use API v1, search calls use API v1.1."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._owns_session = session is None
        self.session = session if session is not None else requests.Session()
        self.timeout = timeout
        if self._owns_session:
            retry = Retry(
                total=2,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET",),
            )
            self.session.mount("https://", HTTPAdapter(max_retries=retry))
            self.session.headers.update({"User-Agent": "metmuseum-tests/1.0"})

    def close(self) -> None:
        """Close a session owned by this client."""
        if self._owns_session:
            self.session.close()

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Log request, response and connection failures."""
        url = f"{BASE_URL}{endpoint}"
        LOGGER.info("Request: GET %s params=%s", url, params)
        started = perf_counter()
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException:
            LOGGER.exception("Request failed: GET %s", url)
            raise

        LOGGER.info(
            "Response: status=%s time=%.3fs url=%s body=%r",
            response.status_code,
            perf_counter() - started,
            response.url,
            response.text[:300],
        )
        if response.status_code >= 400:
            LOGGER.error(
                "HTTP error: status=%s url=%s",
                response.status_code,
                response.url,
            )
        return response

    def artwork(self, object_id: int) -> requests.Response:
        """Fetch a single object by ID."""
        return self._get(f"/v1/objects/{object_id}")

    def search(self, **filters: Any) -> requests.Response:
        """Fetch a page of object IDs."""
        parameters = SearchParameters.model_validate(filters)
        return self._get("/v1.1/search", parameters.to_query())