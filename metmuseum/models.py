"""Pydantic schemas for The Metropolitan Museum of Art API."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArtworkTag(BaseModel):
    """Artwork subject tag."""

    model_config = ConfigDict(strict=True)
    term: str


class ArtworkConstituent(BaseModel):
    """Artwork author or other contributor."""

    model_config = ConfigDict(strict=True)
    constituent_id: int | None = Field(default=None, alias="constituentID")
    role: str
    name: str


class Artwork(BaseModel):
    """Most important artwork properties.

    Other API fields are ignored because they vary by collection.
    """

    model_config = ConfigDict(strict=True, extra="ignore")

    object_id: int = Field(alias="objectID", gt=0)
    title: str
    artist_name: str = Field(alias="artistDisplayName")
    object_date: str = Field(alias="objectDate")
    begin_date: int = Field(alias="objectBeginDate")
    end_date: int = Field(alias="objectEndDate")
    department: str
    object_name: str = Field(alias="objectName")
    medium: str
    is_highlight: bool = Field(alias="isHighlight")
    is_public_domain: bool = Field(alias="isPublicDomain")
    primary_image: str = Field(alias="primaryImage")
    primary_image_small: str = Field(alias="primaryImageSmall")
    additional_images: list[str] | None = Field(alias="additionalImages")
    tags: list[ArtworkTag] | None = None
    constituents: list[ArtworkConstituent] | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "Artwork":
        """Check that creation dates are chronological."""
        if self.begin_date > self.end_date:
            raise ValueError("Invalid artwork creation period")
        return self


class SearchResults(BaseModel):
    """Response from paginated search (including empty pages)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    total: int = Field(ge=0)
    object_ids: list[int] | None = Field(alias="objectIDs")

    @model_validator(mode="after")
    def validate_page(self) -> "SearchResults":
        """Check IDs and total count for internal consistency."""
        if self.object_ids is None:
            return self
        if any(object_id <= 0 for object_id in self.object_ids):
            raise ValueError("objectIDs must contain positive IDs")
        if len(self.object_ids) > self.total:
            raise ValueError("Page exceeds total")
        if len(set(self.object_ids)) != len(self.object_ids):
            raise ValueError("Duplicate IDs in a page")
        return self
