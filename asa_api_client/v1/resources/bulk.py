"""Resource for Apple Ads Platform API v1 bulk operations.

Bulk endpoints live under other resources' paths (``POST
/v1/keywords/bulk-create`` etc.) but are grouped here as one resource.
A bulk request counts as a single call against rate limits regardless
of item count.

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
    BulkItemResultDelete,
    BulkItemResultKeyword,
    BulkItemResultNegativeKeyword,
    BulkKeywordCreate,
    BulkKeywordDelete,
    BulkKeywordUpdate,
    BulkNegativeKeywordCreate,
    BulkNegativeKeywordDelete,
    BulkNegativeKeywordUpdate,
    BulkRequestItem,
)
from asa_api_client.v1.resources.base import V1Resource

DataT = TypeVar("DataT", bound=V1Model)
ResultT = TypeVar("ResultT", bound=V1Model)

#: Maximum items accepted per Apple Ads Platform API v1 bulk request.
MAX_BULK_ITEMS = 5000


class BulkOperationResource(V1Resource[V1Model, V1Model, V1Model]):
    """Batch create/update/delete operations for keywords and negative keywords.

    Endpoints:
        - ``POST /v1/keywords/bulk-create`` — create keywords in bulk
          (items may span different ad groups).
        - ``POST /v1/keywords/bulk-update`` — update keyword
          ``bid``/``status`` in bulk.
        - ``POST /v1/keywords/bulk-delete`` — soft-delete keywords in
          bulk by ID.
        - ``POST /v1/negative-keywords/bulk-create`` — create negative
          keywords in bulk (campaign- and ad-group-level may mix).
        - ``POST /v1/negative-keywords/bulk-update`` — update negative
          keyword ``status`` in bulk.
        - ``POST /v1/negative-keywords/bulk-delete`` — soft-delete
          negative keywords in bulk by ID.

    Items may be passed as bare ``Bulk*`` payloads (or bare integer IDs
    for bulk-delete; a 1-based positional ``correlationId`` is assigned
    automatically) or as explicit :class:`BulkRequestItem` wrappers
    carrying custom correlation IDs. Lists larger than
    :data:`MAX_BULK_ITEMS` (5,000) are automatically split into
    sequential 5,000-item requests with continuous correlation IDs.

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
        *,
        start_id: int = 1,
    ) -> dict[str, Any]:
        """Build the ``{allowPartialSuccess, items}`` request body.

        Args:
            items: Bare data payloads or explicit request items.
            allow_partial_success: The batch's partial-success flag.
            start_id: Starting 1-based ``correlationId`` for bare items.

        Returns:
            The serialized bulk request body.
        """
        wrapped = [
            item
            if isinstance(item, BulkRequestItem)
            else BulkRequestItem(correlation_id=position, data=item)
            for position, item in enumerate(items, start=start_id)
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

    def _execute_bulk(
        self,
        path: str,
        items: Sequence[DataT | BulkRequestItem[DataT]],
        allow_partial_success: bool,
        result_class: type[ResultT],
    ) -> list[ResultT]:
        """Execute a bulk operation synchronously, chunking at ``MAX_BULK_ITEMS``."""
        self._context_header()
        if not items:
            return []

        results: list[ResultT] = []
        for offset in range(0, len(items), MAX_BULK_ITEMS):
            chunk = items[offset : offset + MAX_BULK_ITEMS]
            payload = self._bulk_payload(chunk, allow_partial_success, start_id=offset + 1)
            data = self._request("POST", path, json=payload)
            results.extend(self._parse_results(data, result_class))
        return results

    async def _execute_bulk_async(
        self,
        path: str,
        items: Sequence[DataT | BulkRequestItem[DataT]],
        allow_partial_success: bool,
        result_class: type[ResultT],
    ) -> list[ResultT]:
        """Execute a bulk operation asynchronously, chunking at ``MAX_BULK_ITEMS``."""
        self._context_header()
        if not items:
            return []

        results: list[ResultT] = []
        for offset in range(0, len(items), MAX_BULK_ITEMS):
            chunk = items[offset : offset + MAX_BULK_ITEMS]
            payload = self._bulk_payload(chunk, allow_partial_success, start_id=offset + 1)
            data = await self._request_async("POST", path, json=payload)
            results.extend(self._parse_results(data, result_class))
        return results

    def create_keywords(
        self,
        items: Sequence[BulkKeywordCreate | BulkRequestItem[BulkKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Create multiple keywords in bulk (auto-batched per 5,000 items).

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
        return self._execute_bulk(
            "keywords/bulk-create", items, allow_partial_success, BulkItemResultKeyword
        )

    async def create_keywords_async(
        self,
        items: Sequence[BulkKeywordCreate | BulkRequestItem[BulkKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Create multiple keywords in bulk asynchronously.

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
        return await self._execute_bulk_async(
            "keywords/bulk-create", items, allow_partial_success, BulkItemResultKeyword
        )

    def update_keywords(
        self,
        items: Sequence[BulkKeywordUpdate | BulkRequestItem[BulkKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Update multiple keywords (``bid``/``status``) in bulk.

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
        return self._execute_bulk(
            "keywords/bulk-update", items, allow_partial_success, BulkItemResultKeyword
        )

    async def update_keywords_async(
        self,
        items: Sequence[BulkKeywordUpdate | BulkRequestItem[BulkKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultKeyword]:
        """Update multiple keywords in bulk asynchronously.

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
        return await self._execute_bulk_async(
            "keywords/bulk-update", items, allow_partial_success, BulkItemResultKeyword
        )

    def create_negative_keywords(
        self,
        items: Sequence[BulkNegativeKeywordCreate | BulkRequestItem[BulkNegativeKeywordCreate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultNegativeKeyword]:
        """Create multiple negative keywords in bulk.

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
        return self._execute_bulk(
            "negative-keywords/bulk-create",
            items,
            allow_partial_success,
            BulkItemResultNegativeKeyword,
        )

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
        return await self._execute_bulk_async(
            "negative-keywords/bulk-create",
            items,
            allow_partial_success,
            BulkItemResultNegativeKeyword,
        )

    def update_negative_keywords(
        self,
        items: Sequence[BulkNegativeKeywordUpdate | BulkRequestItem[BulkNegativeKeywordUpdate]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultNegativeKeyword]:
        """Update multiple negative keywords (``status`` only) in bulk.

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
        return self._execute_bulk(
            "negative-keywords/bulk-update",
            items,
            allow_partial_success,
            BulkItemResultNegativeKeyword,
        )

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
        return await self._execute_bulk_async(
            "negative-keywords/bulk-update",
            items,
            allow_partial_success,
            BulkItemResultNegativeKeyword,
        )

    def _normalize_keyword_deletes(
        self,
        items: Sequence[int | BulkKeywordDelete | BulkRequestItem[BulkKeywordDelete]],
    ) -> list[BulkKeywordDelete | BulkRequestItem[BulkKeywordDelete]]:
        """Coerce bare integer keyword IDs into BulkKeywordDelete payloads."""
        return [BulkKeywordDelete(id=item) if isinstance(item, int) else item for item in items]

    def _normalize_negative_keyword_deletes(
        self,
        items: Sequence[
            int | BulkNegativeKeywordDelete | BulkRequestItem[BulkNegativeKeywordDelete]
        ],
    ) -> list[BulkNegativeKeywordDelete | BulkRequestItem[BulkNegativeKeywordDelete]]:
        """Coerce bare integer negative-keyword IDs into BulkNegativeKeywordDelete payloads."""
        return [
            BulkNegativeKeywordDelete(id=item) if isinstance(item, int) else item for item in items
        ]

    def delete_keywords(
        self,
        items: Sequence[int | BulkKeywordDelete | BulkRequestItem[BulkKeywordDelete]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultDelete]:
        """Soft-delete multiple keywords in bulk.

        Args:
            items: Keyword IDs, ``BulkKeywordDelete`` payloads, or
                explicit request items.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item delete outcomes, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        normalized = self._normalize_keyword_deletes(items)
        return self._execute_bulk(
            "keywords/bulk-delete", normalized, allow_partial_success, BulkItemResultDelete
        )

    async def delete_keywords_async(
        self,
        items: Sequence[int | BulkKeywordDelete | BulkRequestItem[BulkKeywordDelete]],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultDelete]:
        """Soft-delete multiple keywords in bulk asynchronously.

        Args:
            items: Keyword IDs, ``BulkKeywordDelete`` payloads, or
                explicit request items.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item delete outcomes, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        normalized = self._normalize_keyword_deletes(items)
        return await self._execute_bulk_async(
            "keywords/bulk-delete", normalized, allow_partial_success, BulkItemResultDelete
        )

    def delete_negative_keywords(
        self,
        items: Sequence[
            int | BulkNegativeKeywordDelete | BulkRequestItem[BulkNegativeKeywordDelete]
        ],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultDelete]:
        """Soft-delete multiple negative keywords in bulk.

        Args:
            items: Negative keyword IDs, ``BulkNegativeKeywordDelete``
                payloads, or explicit request items.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item delete outcomes, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        normalized = self._normalize_negative_keyword_deletes(items)
        return self._execute_bulk(
            "negative-keywords/bulk-delete",
            normalized,
            allow_partial_success,
            BulkItemResultDelete,
        )

    async def delete_negative_keywords_async(
        self,
        items: Sequence[
            int | BulkNegativeKeywordDelete | BulkRequestItem[BulkNegativeKeywordDelete]
        ],
        *,
        allow_partial_success: bool = False,
    ) -> list[BulkItemResultDelete]:
        """Soft-delete multiple negative keywords asynchronously.

        Args:
            items: Negative keyword IDs, ``BulkNegativeKeywordDelete``
                payloads, or explicit request items.
            allow_partial_success: Process valid items and report
                failures per item instead of rejecting the whole batch.

        Returns:
            Per-item delete outcomes, positionally parallel to ``items``.

        Raises:
            PartialFailureError: If the response carries a top-level
                error block (bulk-level rejection).
            ValidationError: If the request body is invalid (HTTP 400).
        """
        normalized = self._normalize_negative_keyword_deletes(items)
        return await self._execute_bulk_async(
            "negative-keywords/bulk-delete",
            normalized,
            allow_partial_success,
            BulkItemResultDelete,
        )
