"""Base models and common types for the Apple Ads Platform API v1.

This module contains the response envelope pieces shared by every v1
endpoint (pagination, error objects, the paginated page container) and
common value types such as :class:`Money`.
"""

from collections.abc import Iterator
from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


class V1Model(BaseModel):
    """Shared base for all v1 API models.

    Applies the package-wide model configuration: camelCase aliases are
    populated by alias or by field name, and unknown fields returned by
    the API are ignored rather than rejected.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Money(V1Model):
    """Represents a monetary amount with currency.

    Attributes:
        amount: The monetary amount as a string to preserve precision.
        currency: The ISO 4217 currency code (e.g., "USD", "AUD").
    """

    amount: str
    currency: str

    @classmethod
    def usd(cls, amount: float | int | str) -> Self:
        """Create a Money instance in USD.

        Args:
            amount: The amount in USD.

        Returns:
            A Money instance with USD currency.
        """
        return cls(amount=str(amount), currency="USD")

    @classmethod
    def of(cls, amount: float | int | str, currency: str) -> Self:
        """Create a Money instance in an arbitrary currency.

        Args:
            amount: The monetary amount.
            currency: The ISO 4217 currency code.

        Returns:
            A Money instance in the given currency.
        """
        return cls(amount=str(amount), currency=currency)


class V1Pagination(V1Model):
    """Pagination metadata on v1 list responses.

    Attributes:
        offset: The starting position for pagination.
        page_size: The number of items per page.
        total_count: The total number of items available server-side.
    """

    offset: int
    page_size: int = Field(alias="pageSize")
    total_count: int = Field(alias="totalCount")


class ErrorDetail(V1Model):
    """One granular entry in a v1 error's ``details`` array.

    Attributes:
        code: Granular reason about one part of the error.
        message: Explicit detail about why this part was rejected.
        info: Endpoint-specific context supplementing the message.
    """

    code: str | None = None
    message: str | None = None
    info: dict[str, Any] | None = None


class V1Error(V1Model):
    """The primary error container in v1 responses.

    Attributes:
        code: The reason the request was rejected.
        message: Human-readable summary of what went wrong.
        details: One or more granular error detail objects.
    """

    code: str | None = None
    message: str | None = None
    details: list[ErrorDetail] | None = None


class V1Page(V1Model, Generic[T]):
    """A page of results from a v1 list or query endpoint.

    Supports iteration, indexing, and ``len()`` over the contained items.

    Attributes:
        result: The items in this page.
        pagination: Pagination metadata, when returned by the server.
    """

    result: list[T] = Field(default_factory=list)
    pagination: V1Pagination | None = None

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        """Iterate over the items in this page."""
        return iter(self.result)

    def __len__(self) -> int:
        """Return the number of items in this page."""
        return len(self.result)

    def __getitem__(self, index: int) -> T:
        """Return the item at the given index."""
        return self.result[index]

    @property
    def has_more(self) -> bool:
        """Whether more items remain on the server beyond this page."""
        if self.pagination is None:
            return False
        return self.pagination.offset + len(self.result) < self.pagination.total_count
