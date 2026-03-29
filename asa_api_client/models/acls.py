"""Access Control List (ACL) models for the Apple Search Ads API.

ACLs define the roles and organizations accessible to an API user.
"""

from pydantic import BaseModel, ConfigDict, Field


class UserAcl(BaseModel):
    """An access control entry for an organization.

    Represents the API user's access to a specific organization,
    including their roles and the organization's payment details.

    Attributes:
        org_id: The organization ID.
        org_name: The organization name.
        currency: The organization's currency code.
        payment_model: The payment model (e.g., "PAYG", "LOC").
        role_names: The user's roles in this organization.
        parent_org_id: The parent organization ID (if applicable).
        time_zone: The organization's timezone.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    org_id: int = Field(alias="orgId")
    org_name: str = Field(alias="orgName")
    currency: str | None = None
    payment_model: str | None = Field(default=None, alias="paymentModel")
    role_names: list[str] = Field(default_factory=list, alias="roleNames")
    parent_org_id: int | None = Field(default=None, alias="parentOrgId")
    time_zone: str | None = Field(default=None, alias="timeZone")
