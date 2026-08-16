"""Resource for Apple Ads Platform API v1 bulk operations.

Bulk endpoints live under other resources' paths (``POST
/v1/keywords/bulk-create`` etc.) but are grouped here as one resource.
A bulk request counts as a single call against rate limits regardless
of item count. Bulk delete endpoints are documented as "coming soon"
and are not implemented; deletion still requires the single-record
endpoints.

By default (``allow_partial_success=False``) any single item failure
rejects the whole batch. With ``allow_partial_success=True`` valid
items are processed and failures are reported per item: the returned
result entries carry ``success=False`` plus a typed ``error``, and the
HTTP status is still 200. A top-level ``error`` block (a bulk-level
rejection such as exceeding the maximum item count, in which case no
items are processed) raises
:class:`~asa_api_client.exceptions.PartialFailureError` via the base
transport.
"""

from collections.abc import Sequence
from typing import Any, TypeVar

from asa_api_client.v1.models.base import V1Model
from asa_api_client.v1.models.bulk import (
    BulkItemResultKeyword,
    BulkItemResultNegativeKeyword,
    BulkKeywordCreate,
    BulkKeywordUpdate,
    BulkNegativeKeywordCreate,
    BulkNegativeKeywordUpdate,
    BulkRequestItem,
)
from asa_api_client.v1.resources.base import V1Resource

DataT = TypeVar("DataT", bound=V1Model)
ResultT = TypeVar("ResultT", bound=V1Model)


class BulkOperationResource(V1Resource[V1Model, V1Model, V1Model]):
    """Batch create/update operations for keywords and negative keywords.

    Endpoints:
        - ``POST /v1/keywords/bulk-create`` — create keywords in bulk
          (items may span different ad groups).
        - ``POST /v1/keywords/bulk-update`` — update keyword
          ``bid``/``status`` in bulk.
        - ``POST /v1/negative-keywords/bulk-create`` — create negative
          keywords in bulk (campaign- and ad-group-level may mix).
        - ``POST /v1/negative-keywords/bulk-update`` — update negative
          keyword ``status`` in bulk.

    Items may be passed as bare ``Bulk*Create``/``Bulk*Update`` payloads
    (a 1-based positional ``correlationId`` is assigned automatically)
    or as explicit :class:`BulkRequestItem` wrappers carrying custom
    correlation IDs.

    Example:
        Pause two keywords in one call::

            from asa_api_client.v1.models.bulk import BulkKeywordUpdate
            from asa_api_client.v1.models.keywords import KeywordStatus

            results = client.bulk.update_keywords(
                [
                    BulkKeywordUpdate(id=300, status=KeywordStatus.PAUSED),
                    BulkKeywordUpdate(id=301, status=KeywordStatus.PAUSED),
                ],
                allow_partial_success=True,
            )
            failed = [r for r in results if not r.success]
    """

    base_path = ""
    model_class = V1Model
    requires_account_context = True

    def _bulk_payload(
        self,
        items: Sequence[DataT | BulkRequestItem[DataT]],
        allow_partial_success: bool,
    ) -> dict[str, Any]:
        """Build the ``{allowPartialSuccess, items}`` request body.

        Args:
            items: Bare data payloads or explicit request items.
            allow_partial_success: The batch's partial-success flag.

        Returns:
            The serialized bulk request body.
        """
        wrapped = [
            item
            if isinstance(item, BulkRequestItem)
            else BulkRequestItem(correlation_id=position, data=item)
            for position, item in enumerate(items, start=1)
        ]
        return {
            "allowPartialSuccess": allow_partial_success,
            "items": [self._dump(item) for item in wrapped],
        }

    def _parse_results(self, data: dict[str, Any], result_class: type[ResultT]) -> list[ResultT]:
        """Parse the response ``result`` array into typed item results.

        Args:
            data: The API response body.
            result_class: The per-item result model to validate into.

        Returns:
            One typed result per request item, in request order.
        """
        return [result_class.model_validate(entry) for entry in data.get("result") or []]

    def create_keywords(
        self,
        items: Sequence[BulkKeywordCreate | BulkRequestItem[BulkKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Create multiple keywords in a single request.

        Args:
            items: Keyword create payloads (or explicit request items).
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = self._request("POST", "keywords/bulk-create", json=payload)
        return self._parse_results(data, BulkItemResultKeyword)

    async def create_keywords_async(
        self,
        items: Sequence[BulkKeywordCreate | BulkRequestItem[BulkKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Create multiple keywords in a single request asynchronously.

        Args:
            items: Keyword create payloads (or explicit request items).
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = await self._request_async("POST", "keywords/bulk-create", json=payload)
        return self._parse_results(data, BulkItemResultKeyword)

    def update_keywords(
        self,
        items: Sequence[BulkKeywordUpdate | BulkRequestItem[BulkKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Update multiple keywords (``bid``/``status``) in one request.

        Args:
            items: Keyword update payloads (or explicit request items);
                each must carry the target keyword ``id``.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = self._request("POST", "keywords/bulk-update", json=payload)
        return self._parse_results(data, BulkItemResultKeyword)

    async def update_keywords_async(
        self,
        items: Sequence[BulkKeywordUpdate | BulkRequestItem[BulkKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Update multiple keywords in one request asynchronously.

        Args:
            items: Keyword update payloads (or explicit request items);
                each must carry the target keyword ``id``.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = await self._request_async("POST", "keywords/bulk-update", json=payload)
        return self._parse_results(data, BulkItemResultKeyword)

    def create_negative_keywords(
        self,
        items: Sequence[BulkNegativeKeywordCreate | BulkRequestItem[BulkNegativeKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultNegativeKeyword]:
        """Create multiple negative keywords in a single request.

        Campaign-level (``campaign_id`` only) and ad-group-level
        (``campaign_id`` + ``ad_group_id``) negatives may be mixed.

        Args:
            items: Negative keyword create payloads (or explicit
                request items).
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = self._request("POST", "negative-keywords/bulk-create", json=payload)
        return self._parse_results(data, BulkItemResultNegativeKeyword)

    async def create_negative_keywords_async(
        self,
        items: Sequence[BulkNegativeKeywordCreate | BulkRequestItem[BulkNegativeKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultNegativeKeyword]:
        """Create multiple negative keywords asynchronously.

        Args:
            items: Negative keyword create payloads (or explicit
                request items).
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = await self._request_async("POST", "negative-keywords/bulk-create", json=payload)
        return self._parse_results(data, BulkItemResultNegativeKeyword)

    def update_negative_keywords(
        self,
        items: Sequence[BulkNegativeKeywordUpdate | BulkRequestItem[BulkNegativeKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultNegativeKeyword]:
        """Update multiple negative keywords (``status`` only) in one request.

        Args:
            items: Negative keyword update payloads (or explicit
                request items); each must carry the target ``id``.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = self._request("POST", "negative-keywords/bulk-update", json=payload)
        return self._parse_results(data, BulkItemResultNegativeKeyword)

    async def update_negative_keywords_async(
        self,
        items: Sequence[BulkNegativeKeywordUpdate | BulkRequestItem[BulkNegativeKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultNegativeKeyword]:
        """Update multiple negative keywords asynchronously.

        Args:
            items: Negative keyword update payloads (or explicit
                request items); each must carry the target ``id``.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item results, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        payload = self._bulk_payload(items, allow_partial_success)
        data = await self._request_async("POST", "negative-keywords/bulk-update", json=payload)
        return self._parse_results(data, BulkItemResultNegativeKeyword)
