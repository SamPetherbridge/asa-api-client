"""Ad groups resource for Apple Ads Platform API v1.

Implements the five documented ``/v1/adgroups`` endpoints: create,
query, get, update, and (soft) delete. Create and update bodies are
sent flat — the v1 ad-group endpoints use no payload wrapper.
"""

from asa_api_client.v1.models.ad_groups import AdGroup, AdGroupCreate, AdGroupUpdate
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)


class AdGroupResource(
    GettableMixin[AdGroup, AdGroupCreate, AdGroupUpdate],
    QueryableMixin[AdGroup, AdGroupCreate, AdGroupUpdate],
    CreatableMixin[AdGroup, AdGroupCreate, AdGroupUpdate],
    UpdatableMixin[AdGroup, AdGroupCreate, AdGroupUpdate],
    DeletableMixin[AdGroup, AdGroupCreate, AdGroupUpdate],
    V1Resource[AdGroup, AdGroupCreate, AdGroupUpdate],
):
    """Manage ad groups (``/v1/adgroups``).

    Endpoints:
        - ``POST /v1/adgroups`` — :meth:`create`
        - ``POST /v1/adgroups/query`` — :meth:`query` / :meth:`iter_all`
        - ``GET /v1/adgroups/{id}`` — :meth:`get`
        - ``PUT /v1/adgroups/{id}`` — :meth:`update`
        - ``DELETE /v1/adgroups/{id}`` — :meth:`delete`

    Deletion is a soft delete that cascades to the ad group's ads,
    keywords, and negative keywords. Deleted ad groups are excluded
    from query results by default (filter ``deleted EQUALS true`` to
    include them) but are still returned by :meth:`get`.

    Example:
        Pause every ad group in a campaign::

            from asa_api_client.v1.models.ad_groups import (
                AdGroupStatus,
                AdGroupUpdate,
            )
            from asa_api_client.v1.query import Query

            resource = AdGroupResource(client)
            query = Query().where("campaignId", "EQUALS", 1000)
            for ad_group in resource.iter_all(query):
                if ad_group.id is not None:
                    resource.update(
                        ad_group.id,
                        AdGroupUpdate(status=AdGroupStatus.PAUSED),
                    )
    """

    base_path = "adgroups"
    model_class = AdGroup
