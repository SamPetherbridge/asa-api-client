"""Models for the Apple Ads Platform API v1 change history endpoints.

Change history is a chronological audit log of every CREATE, UPDATE, and
DELETE performed on entities in an ad account. The query endpoint returns
transaction-grouped :class:`AuditSummary` rows; the detail endpoint
returns field-level before/after values as :class:`ChangeDetails`.

Note:
    The change-history error object (:class:`ErrorMessage`) is specific
    to this group and uses a closed code enum
    (:class:`ErrorMessageCode`), unlike the general API error object.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field

from asa_api_client.v1.models.base import V1Model


class AuditEventType(StrEnum):
    """The kind of change an audit record describes.

    Attributes:
        CREATE: New entity created; ``oldValues`` are empty.
        UPDATE: One or more fields modified; both value sets populated.
        DELETE: Soft-delete; implemented as a record update, so
            ``newValues`` may carry system-managed values (deletion
            flag, status, transaction ID).
    """

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AuditUserType(StrEnum):
    """The kind of actor that made a change.

    Attributes:
        CUSTOMER: Human user via the Apple Ads UI.
        CUSTOMER_API: Automated process via the Apple Ads Platform API.
        APPLE_SUPPORT: Apple support representative acting on behalf
            of an advertiser.
    """

    CUSTOMER = "CUSTOMER"
    CUSTOMER_API = "CUSTOMER_API"
    APPLE_SUPPORT = "APPLE_SUPPORT"


class AuditOperator(StrEnum):
    """Filter operators accepted by the change-history query endpoint.

    ``BETWEEN`` / ``GREATER_THAN`` / ``LESS_THAN`` apply to the
    mandatory ``eventTime`` filter; other fields support ``EQUALS``
    and ``IN``.
    """

    EQUALS = "EQUALS"
    IN = "IN"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL_TO = "LESS_THAN_OR_EQUAL_TO"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL_TO = "GREATER_THAN_OR_EQUAL_TO"
    BETWEEN = "BETWEEN"


class AuditSortOrder(StrEnum):
    """Sort direction for change-history query sorting entries.

    Attributes:
        ASC: Smallest/earliest first.
        DESC: Largest/most recent first (the default when omitted).
    """

    ASC = "ASC"
    DESC = "DESC"


class ErrorMessageCode(StrEnum):
    """Closed set of top-level change-history error codes.

    General API error codes (e.g. ``INVALID_ARGUMENT``) do not apply
    to change-history responses.
    """

    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    NOT_AUTHED = "NOT_AUTHED"


class ErrorMessageDetail(V1Model):
    """One field-level entry in a change-history error's details array.

    Attributes:
        code: Machine-readable validation-failure code (open set,
            e.g. ``MISSING_FIELD``).
        message: Human-readable detail.
        info: Additional structured context, e.g.
            ``{"field": "eventTime"}``.
    """

    code: str | None = None
    message: str | None = None
    info: dict[str, str] | None = None


class ErrorMessage(V1Model):
    """The change-history-specific error object.

    This is NOT the general API error object: its ``code`` is the
    closed :class:`ErrorMessageCode` enum.

    Attributes:
        code: Top-level error code.
        message: Human-readable summary.
        details: Field-level context entries.
    """

    code: ErrorMessageCode | None = None
    message: str | None = None
    details: list[ErrorMessageDetail] | None = None


class AuditSummaryMeta(V1Model):
    """Per-entity metadata entry on an :class:`AuditSummary` row.

    Each entry carries one dynamic key named after the entity type
    (e.g. ``"Campaign"``) whose value is the entity ID; dynamic keys
    are preserved and exposed via :attr:`entity_ids`.

    Attributes:
        detail_id: Ready-to-use composite ID
            (``EntityType.entityId.txnId``) for the detail endpoint.
        meta: Entity state — current (``latest``) or at event time
            (``snapshot``), per the query's ``options.metadata``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    detail_id: str | None = Field(default=None, alias="detailId")
    meta: dict[str, Any] | None = None

    @property
    def entity_ids(self) -> dict[str, str]:
        """Map of dynamic entity-type keys to entity ID values.

        Returns:
            A dict such as ``{"Campaign": "444555666"}`` built from
            the entry's dynamic keys.
        """
        return {
            key: value for key, value in (self.model_extra or {}).items() if isinstance(value, str)
        }


class AuditSummary(V1Model):
    """One transaction-grouped row in the change-history query response.

    Attributes:
        transaction_id: Transaction identifier (matches the ``txnId``
            filter field). A component of the composite detail ID.
        event_type: CREATE / UPDATE / DELETE.
        event_time: When the change happened (always UTC).
        entity_type: API entity name; an open string, not an enum
            (Campaign, AdGroup, Keyword, AdAccount, Org, ...).
        count: Number of entity changes in this grouping.
        metas: Per-entity metadata; empty unless the query set
            ``options.metadata`` to ``latest`` or ``snapshot``.
        user_type: The kind of actor that made the change.
        modified_by: User/service identifier (never an email).
    """

    transaction_id: str | None = Field(default=None, alias="transactionId")
    event_type: AuditEventType | None = Field(default=None, alias="eventType")
    event_time: datetime | None = Field(default=None, alias="eventTime")
    entity_type: str | None = Field(default=None, alias="entityType")
    count: int | None = None
    metas: list[AuditSummaryMeta] = Field(default_factory=list)
    user_type: AuditUserType | None = Field(default=None, alias="userType")
    modified_by: str | None = Field(default=None, alias="modifiedBy")


class ActivityChange(V1Model):
    """One changed field within an :class:`ActivityDetail`.

    All values are strings regardless of the underlying field type
    (e.g. ``"50.00"`` for a budget); scalar fields appear as
    single-element arrays.

    Attributes:
        field: API field name that changed.
        old_values: Values before the change (empty for CREATE).
        new_values: Values after the change (usually empty for DELETE,
            though soft-deletes may set system-managed values).
    """

    field: str | None = None
    old_values: list[str] = Field(default_factory=list, alias="oldValues")
    new_values: list[str] = Field(default_factory=list, alias="newValues")


class ActivityDetail(V1Model):
    """A group of field-level changes within one transaction.

    Attributes:
        transaction_id: Matches the parent record's transaction ID.
        changes: One entry per changed field.
    """

    transaction_id: str | None = Field(default=None, alias="transactionId")
    changes: list[ActivityChange] = Field(default_factory=list)


class ChangeDetails(V1Model):
    """Field-level change record for a single entity within a transaction.

    Attributes:
        transaction_id: Transaction identifier.
        detail_id: Unique per entity change within the transaction
            (composite ``EntityType.entityId.txnId``).
        event_type: CREATE / UPDATE / DELETE.
        entity_type: API entity name (open string, not an enum).
        entity_id: Platform ID of the changed entity.
        event_time: When the change happened (always UTC).
        user_type: The kind of actor that made the change.
        modified_by: User/service identifier.
        entity_meta_data: String map of entity metadata; the key set
            varies by entity type (e.g. ``name``, ``campaignId``).
        details: Grouped field-level changes.
    """

    transaction_id: str | None = Field(default=None, alias="transactionId")
    detail_id: str | None = Field(default=None, alias="detailId")
    event_type: AuditEventType | None = Field(default=None, alias="eventType")
    entity_type: str | None = Field(default=None, alias="entityType")
    entity_id: str | None = Field(default=None, alias="entityId")
    event_time: datetime | None = Field(default=None, alias="eventTime")
    user_type: AuditUserType | None = Field(default=None, alias="userType")
    modified_by: str | None = Field(default=None, alias="modifiedBy")
    entity_meta_data: dict[str, str] | None = Field(default=None, alias="entityMetaData")
    details: list[ActivityDetail] = Field(default_factory=list)
