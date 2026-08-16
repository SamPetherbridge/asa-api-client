"""Resource for the Apple Ads Platform API v1 ads endpoints.

Covers create, query, get, update, and delete of ads — the atomic
serving units that link an ad creative to an ad group.
"""

from asa_api_client.v1.models.ads import Ad, AdCreate, AdUpdate
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)


class AdResource(
    GettableMixin[Ad, AdCreate, AdUpdate],
    QueryableMixin[Ad, AdCreate, AdUpdate],
    CreatableMixin[Ad, AdCreate, AdUpdate],
    UpdatableMixin[Ad, AdCreate, AdUpdate],
    DeletableMixin[Ad, AdCreate, AdUpdate],
    V1Resource[Ad, AdCreate, AdUpdate],
):
    """Ads within an ad account (``/v1/ads``).

    Endpoints:
        - ``POST /v1/ads`` — :meth:`create` (bare ``AdCreate`` body).
        - ``POST /v1/ads/query`` — :meth:`query` / :meth:`iter_all`.
        - ``GET /v1/ads/{id}`` — :meth:`get` (returns soft-deleted
          ads too, with ``deleted: true``).
        - ``PUT /v1/ads/{id}`` — :meth:`update` (only ``name`` and
          ``status`` are mutable; 404 for deleted ads).
        - ``DELETE /v1/ads/{id}`` — :meth:`delete` (soft-delete; the
          API responds 200 with an empty JSON object).

    Notes:
        Query results exclude deleted ads by default; filter
        ``deleted EQUALS true`` to retrieve them. Only one ad per ad
        group can be ``ENABLED`` at a time, and an ad cannot be
        enabled until its parent ad group and campaign are enabled.
    """

    base_path = "ads"
    model_class = Ad
