"""Change history resource for the Apple Ads Platform API v1.

Read-only audit log under ``/v1/change-history``. The query endpoint
uses a non-standard body (an extra top-level ``options`` string map),
and the detail endpoint's ``limit``/``offset`` query parameters page
through the ``changes`` array *inside* a single record — not through
records — so both endpoints are explicit methods rather than mixins.
"""

from typing import Any

from asa_api_client.v1.models.base import V1Page, V1Pagination
from asa_api_client.v1.models.change_history import AuditSummary, ChangeDetails
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.base import V1Resource


class ChangeHistoryResource(V1Resource[AuditSummary, AuditSummary, AuditSummary]):
    """Change history audit log (``/v1/change-history``). Read-only.

    Every query MUST include an ``eventTime`` filter (``BETWEEN``,
    ``GREATER_THAN``, or ``LESS_THAN``; max lookback six months) or the
    API returns 400. All ``options`` values are strings — including
    ``needTotals`` (``"true"``/``"false"``).

    Example:
        Query recent campaign changes with ready-made detail IDs::

            page = client.change_history.query(
                Query()
                .where("eventTime", "GREATER_THAN", "2026-02-01T00:00:00")
                .where("entityType", "IN", ["Campaign"]),
                options={"metadata": "latest"},
            )
            details = client.change_history.get_details(
                page[0].metas[0].detail_id
            )
    """

    base_path = "change-history"
    model_class = AuditSummary

    def _query_payload(self, query: Query | None, options: dict[str, str] | None) -> dict[str, Any]:
        """Build the audit query body.

        Args:
            query: The filters/sorting/pagination builder. The
                change-history filter shape (``{field, operator,
                value}``) matches what :class:`Query` produces.
            options: Optional string→string options map
                (``needTotals``, ``timeZone``, ``metadata``).

        Returns:
            The ``{filters, sorting, pagination, options}`` body,
            omitting empty sections.
        """
        payload = query.to_payload() if query is not None else {}
        if options:
            payload["options"] = options
        return payload

    def query(
        self,
        query: Query | None = None,
        *,
        options: dict[str, str] | None = None,
    ) -> V1Page[AuditSummary]:
        """Query audit summaries grouped by transaction.

        Args:
            query: Query with filters/sorting/pagination. An
                ``eventTime`` filter is mandatory (400 without one).
            options: Optional options map; all values are strings.
                Keys: ``needTotals`` (``"true"``/``"false"``),
                ``timeZone`` (``"UTC"``/``"ORTZ"``), ``metadata``
                (``"none"``/``"latest"``/``"snapshot"``). Set
                ``metadata`` to ``"latest"`` or ``"snapshot"`` to get
                ready-to-use ``detailId`` values in each row's metas.

        Returns:
            A page of matching audit summary rows.

        Raises:
            ValidationError: If the query lacks an eventTime filter.
        """
        data = self._request("POST", "query", json=self._query_payload(query, options))
        return self._parse_page(data)

    async def query_async(
        self,
        query: Query | None = None,
        *,
        options: dict[str, str] | None = None,
    ) -> V1Page[AuditSummary]:
        """Query audit summaries grouped by transaction, asynchronously.

        Args:
            query: Query with filters/sorting/pagination. An
                ``eventTime`` filter is mandatory (400 without one).
            options: Optional options map; all values are strings.

        Returns:
            A page of matching audit summary rows.

        Raises:
            ValidationError: If the query lacks an eventTime filter.
        """
        data = await self._request_async("POST", "query", json=self._query_payload(query, options))
        return self._parse_page(data)

    @staticmethod
    def _details_params(limit: int | None, offset: int | None) -> dict[str, Any] | None:
        """Build the detail endpoint's query parameters.

        Args:
            limit: Maximum ``changes`` entries returned (default 100).
            offset: Zero-based index of the first ``changes`` entry.

        Returns:
            The parameter dict, or None when both are unset.
        """
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return params or None

    def _parse_details_page(self, data: dict[str, Any]) -> V1Page[ChangeDetails]:
        """Parse a detail response into a typed page.

        Args:
            data: The API response body.

        Returns:
            A page of :class:`ChangeDetails` records.
        """
        items = [ChangeDetails.model_validate(item) for item in data.get("result") or []]
        pagination_data = data.get("pagination")
        pagination = V1Pagination.model_validate(pagination_data) if pagination_data else None
        return V1Page[ChangeDetails](result=items, pagination=pagination)

    def get_details(
        self,
        detail_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> V1Page[ChangeDetails]:
        """Get field-level before/after values for a single change.

        Note:
            ``limit``/``offset`` page through the ``changes`` array
            inside the record, not through records.

        Args:
            detail_id: Composite ID ``EntityType.entityId.txnId``
                (e.g. ``Campaign.444555666.txn_abc123def456``).
            limit: Maximum ``changes`` entries returned (default 100).
            offset: Zero-based index of the first ``changes`` entry.

        Returns:
            A page of change detail records.

        Raises:
            NotFoundError: If the detail ID is unknown.
        """
        data = self._request("GET", detail_id, params=self._details_params(limit, offset))
        return self._parse_details_page(data)

    async def get_details_async(
        self,
        detail_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> V1Page[ChangeDetails]:
        """Get field-level change details asynchronously.

        Args:
            detail_id: Composite ID ``EntityType.entityId.txnId``.
            limit: Maximum ``changes`` entries returned (default 100).
            offset: Zero-based index of the first ``changes`` entry.

        Returns:
            A page of change detail records.

        Raises:
            NotFoundError: If the detail ID is unknown.
        """
        data = await self._request_async(
            "GET", detail_id, params=self._details_params(limit, offset)
        )
        return self._parse_details_page(data)
