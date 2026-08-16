"""Creatives and assets resources for the Apple Ads Platform API v1.

Creatives are account-level entities defining an ad's visual
presentation and tap destination; assets are unified media entities
(currently images only) referenced from creative specs.
"""

from typing import IO

import httpx

from asa_api_client.v1.models.creatives import (
    Asset,
    Creative,
    CreativeCreate,
    CreativeUpdate,
)
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)

#: The only promoted object type accepted by the asset upload endpoint.
UPLOAD_PROMOTED_OBJECT_TYPE = "BUSINESS_BRAND"


class CreativeResource(
    GettableMixin[Creative, CreativeCreate, CreativeUpdate],
    QueryableMixin[Creative, CreativeCreate, CreativeUpdate],
    CreatableMixin[Creative, CreativeCreate, CreativeUpdate],
    UpdatableMixin[Creative, CreativeCreate, CreativeUpdate],
    DeletableMixin[Creative, CreativeCreate, CreativeUpdate],
    V1Resource[Creative, CreativeCreate, CreativeUpdate],
):
    """Ad creatives: visual presentation plus tap destination.

    Endpoints:
        - ``POST /v1/creatives`` — create.
        - ``POST /v1/creatives/query`` — query.
        - ``GET /v1/creatives/{id}`` — get by id.
        - ``PUT /v1/creatives/{id}`` — update (name/creativeSpec only).
        - ``DELETE /v1/creatives/{id}`` — soft-delete (irreversible).

    Note:
        Fetching a deleted creative by id returns 404; query with a
        ``deleted: true`` filter instead. Query results are
        auto-scoped to accessible ad accounts and cannot be filtered
        by ``adAccountId``.
    """

    base_path = "creatives"
    model_class = Creative


class AssetResource(
    GettableMixin[Asset, Asset, Asset],
    QueryableMixin[Asset, Asset, Asset],
    DeletableMixin[Asset, Asset, Asset],
    V1Resource[Asset, Asset, Asset],
):
    """Unified media assets referenced from creative specs.

    Endpoints:
        - ``POST /v1/assets/upload`` — upload an image (multipart).
        - ``POST /v1/assets/query`` — query.
        - ``GET /v1/assets/{id}`` — get by id (includes deleted assets).
        - ``DELETE /v1/assets/{id}`` — soft-delete (uploaded assets
          only).

    Note:
        Query results exclude deleted assets and variant assets
        (crops); retrieve variants via :meth:`GettableMixin.get`.
        Apple recommends always filtering queries by
        ``promotedObjectId``.
    """

    base_path = "assets"
    model_class = Asset

    def upload(
        self,
        file: bytes | IO[bytes],
        *,
        promoted_object_id: str,
        promoted_object_type: str = UPLOAD_PROMOTED_OBJECT_TYPE,
        file_name: str = "asset",
    ) -> Asset:
        """Upload a binary image file to create a new asset.

        The asset processes asynchronously after upload — poll
        :meth:`GettableMixin.get` until ``eligibility.status`` shows
        ready before referencing it in a creative.

        Args:
            file: The image file bytes or a binary file object.
                Accepted formats: PNG, JPG, HEIC.
            promoted_object_id: Identifier of the promoted object
                (e.g. brand ID for ``BUSINESS_BRAND``).
            promoted_object_type: Promoted object type; the upload
                endpoint accepts only ``BUSINESS_BRAND``.
            file_name: Filename to attach to the multipart part.

        Returns:
            The created asset, with a provider-assigned
            ``providerAssetId``.

        Raises:
            ValidationError: If the file or parameters are invalid.
            PartialFailureError: If a 2xx response carries an error
                block.
        """
        response = self._http_client.post(
            self._build_url("upload"),
            files={"file": (file_name, file)},
            data=self._upload_form(promoted_object_id, promoted_object_type),
            headers=self._upload_headers(self._get_headers()),
        )
        return self._finish_upload(response)

    async def upload_async(
        self,
        file: bytes | IO[bytes],
        *,
        promoted_object_id: str,
        promoted_object_type: str = UPLOAD_PROMOTED_OBJECT_TYPE,
        file_name: str = "asset",
    ) -> Asset:
        """Upload a binary image file asynchronously.

        Args:
            file: The image file bytes or a binary file object.
                Accepted formats: PNG, JPG, HEIC.
            promoted_object_id: Identifier of the promoted object.
            promoted_object_type: Promoted object type; the upload
                endpoint accepts only ``BUSINESS_BRAND``.
            file_name: Filename to attach to the multipart part.

        Returns:
            The created asset.

        Raises:
            ValidationError: If the file or parameters are invalid.
            PartialFailureError: If a 2xx response carries an error
                block.
        """
        response = await self._async_http_client.post(
            self._build_url("upload"),
            files={"file": (file_name, file)},
            data=self._upload_form(promoted_object_id, promoted_object_type),
            headers=self._upload_headers(await self._get_headers_async()),
        )
        return self._finish_upload(response)

    @staticmethod
    def _upload_form(promoted_object_id: str, promoted_object_type: str) -> dict[str, str]:
        """Build the non-file multipart form fields for an upload.

        Args:
            promoted_object_id: Identifier of the promoted object.
            promoted_object_type: Promoted object type.

        Returns:
            The form-field dict with camelCase part names.
        """
        return {
            "promotedObjectId": promoted_object_id,
            "promotedObjectType": promoted_object_type,
        }

    @staticmethod
    def _upload_headers(headers: dict[str, str]) -> dict[str, str]:
        """Adapt standard request headers for a multipart upload.

        Drops ``Content-Type: application/json`` so httpx can set the
        multipart boundary itself.

        Args:
            headers: The standard JSON request headers.

        Returns:
            Headers suitable for a multipart request.
        """
        return {key: value for key, value in headers.items() if key != "Content-Type"}

    def _finish_upload(self, response: httpx.Response) -> Asset:
        """Validate and parse an upload response.

        Args:
            response: The HTTP response from the upload endpoint.

        Returns:
            The parsed asset.

        Raises:
            AppleSearchAdsError: Mapped from the HTTP status on 4xx/5xx.
            PartialFailureError: If a 2xx body carries an error block.
        """
        if response.status_code >= 400:
            self._handle_error(response)
        body = response.json()
        self._check_body_error(body, response.status_code)
        return self._parse_item(body)
