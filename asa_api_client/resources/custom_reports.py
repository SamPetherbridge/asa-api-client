"""Custom Reports resource for the Apple Search Ads API.

Provides methods for creating and retrieving impression share reports.
"""

import asyncio
import builtins
import csv
import io
import sys
import time
from datetime import date
from typing import TYPE_CHECKING, Any

import httpx

from asa_api_client.exceptions import AppleSearchAdsError, NetworkError
from asa_api_client.logging import get_logger
from asa_api_client.models.reports import (
    GranularityType,
    ImpressionShareDateRange,
    ImpressionShareReport,
    ImpressionShareReportRow,
)
from asa_api_client.resources.base import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_INITIAL_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    RETRYABLE_STATUS_CODES,
)

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient

logger = get_logger(__name__)


class CustomReportResource:
    """Resource for creating and retrieving impression share reports.

    Impression share reports show your share of impressions for keywords
    compared to total available impressions. These reports are generated
    asynchronously - you create a report, then poll for completion.

    Note:
        - Limited to last 12 weeks of data
        - Only DAILY or WEEKLY granularity supported
        - WEEKLY reports require a dateRange parameter

    Example:
        Create and wait for an impression share report::

            from datetime import date, timedelta

            # Create report
            report = client.custom_reports.create_impression_share(
                start_date=date.today() - timedelta(days=7),
                end_date=date.today() - timedelta(days=1),
                granularity=GranularityType.DAILY,
            )

            # Wait for completion
            report = client.custom_reports.wait_for_report(report.id)

            # Process results
            for row in report.row:
                share = f"{row.low_impression_share}-{row.high_impression_share}%"
                print(f"{row.metadata.keyword}: {share}")

        Or use the convenience method that handles polling::

            report = client.custom_reports.get_impression_share(
                start_date=date.today() - timedelta(days=7),
                end_date=date.today() - timedelta(days=1),
            )
    """

    base_path = "custom-reports"

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the custom reports resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        self._client = client

    @property
    def _http_client(self) -> httpx.Client:
        """Get the sync HTTP client."""
        return self._client._get_http_client()

    @property
    def _async_http_client(self) -> httpx.AsyncClient:
        """Get the async HTTP client."""
        return self._client._get_async_http_client()

    def _build_url(self, path: str = "") -> str:
        """Build the full API URL."""
        base = self._client._base_url.rstrip("/")
        resource_path = self.base_path.strip("/")
        extra = path.strip("/") if path else ""
        if extra:
            return f"{base}/{resource_path}/{extra}"
        return f"{base}/{resource_path}"

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        token = self._client._authenticator.get_access_token(self._http_client)
        return {
            "Authorization": token.authorization_header,
            "X-AP-Context": f"orgId={self._client.org_id}",
            "Content-Type": "application/json",
        }

    async def _get_headers_async(self) -> dict[str, str]:
        """Get headers for async API requests."""
        token = await self._client._authenticator.get_access_token_async(self._async_http_client)
        return {
            "Authorization": token.authorization_header,
            "X-AP-Context": f"orgId={self._client.org_id}",
            "Content-Type": "application/json",
        }

    def _calculate_retry_delay(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate delay before next retry attempt.

        Args:
            attempt: Current attempt number (0-indexed).
            response: The HTTP response (to check Retry-After header).

        Returns:
            Delay in seconds before next retry.
        """
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), DEFAULT_MAX_DELAY)
                except ValueError:
                    pass
        delay = DEFAULT_INITIAL_DELAY * (DEFAULT_BACKOFF_FACTOR**attempt)
        return min(delay, DEFAULT_MAX_DELAY)

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle an error response from the API."""
        from asa_api_client.resources.base import BaseResource

        base = BaseResource.__new__(BaseResource)
        base._client = self._client
        base._handle_error(response)

    def _request(
        self,
        method: str,
        path: str = "",
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> dict[str, Any]:
        """Make a synchronous API request with automatic retry.

        Automatically retries on rate limiting (429) and server errors (5xx)
        with exponential backoff.
        """
        url = self._build_url(path)
        headers = self._get_headers()
        logger.debug("%s %s", method, url)

        last_exception: AppleSearchAdsError | None = None

        for attempt in range(max_retries + 1):
            try:
                response = self._http_client.request(
                    method, url, json=json, params=params, headers=headers
                )
            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        str(e),
                    )
                    time.sleep(delay)
                    continue
                raise NetworkError(f"Request failed: {e}") from e

            # Check if we should retry based on status code
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                delay = self._calculate_retry_delay(attempt, response)
                # Log to both logger and stderr for visibility
                msg = (
                    f"Rate limited ({response.status_code}), "
                    f"attempt {attempt + 1}/{max_retries + 1}, retrying in {delay:.0f}s..."
                )
                logger.warning(msg)
                print(f"⏳ {msg}", file=sys.stderr)
                time.sleep(delay)
                continue

            if response.status_code >= 400:
                self._handle_error(response)

            if response.status_code == 204:
                return {}

            result: dict[str, Any] = response.json()
            return result

        if last_exception:
            raise last_exception
        raise NetworkError("Request failed after all retries")

    async def _request_async(
        self,
        method: str,
        path: str = "",
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> dict[str, Any]:
        """Make an asynchronous API request with automatic retry.

        Automatically retries on rate limiting (429) and server errors (5xx)
        with exponential backoff.
        """
        url = self._build_url(path)
        headers = await self._get_headers_async()
        logger.debug("%s %s (async)", method, url)

        last_exception: AppleSearchAdsError | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self._async_http_client.request(
                    method, url, json=json, params=params, headers=headers
                )
            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        str(e),
                    )
                    await asyncio.sleep(delay)
                    continue
                raise NetworkError(f"Request failed: {e}") from e

            # Check if we should retry based on status code
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                delay = self._calculate_retry_delay(attempt, response)
                msg = (
                    f"Rate limited ({response.status_code}), "
                    f"attempt {attempt + 1}/{max_retries + 1}, retrying in {delay:.0f}s..."
                )
                logger.warning(msg)
                print(f"⏳ {msg}", file=sys.stderr)
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 400:
                self._handle_error(response)

            if response.status_code == 204:
                return {}

            result: dict[str, Any] = response.json()
            return result

        if last_exception:
            raise last_exception
        raise NetworkError("Request failed after all retries")

    def list_reports(
        self, limit: int = 100, offset: int = 0
    ) -> "builtins.list[ImpressionShareReport]":
        """List all impression share reports.

        Args:
            limit: Maximum number of reports to return.
            offset: Number of reports to skip.

        Returns:
            List of impression share reports.
        """
        params = {"limit": limit, "offset": offset}
        data = self._request("GET", "", params=params)

        reports: builtins.list[ImpressionShareReport] = []
        for item in data.get("data", []):
            reports.append(ImpressionShareReport.model_validate(item))
        return reports

    async def list_reports_async(
        self, limit: int = 100, offset: int = 0
    ) -> "builtins.list[ImpressionShareReport]":
        """List all impression share reports asynchronously.

        Args:
            limit: Maximum number of reports to return.
            offset: Number of reports to skip.

        Returns:
            List of impression share reports.
        """
        params = {"limit": limit, "offset": offset}
        data = await self._request_async("GET", "", params=params)

        reports: builtins.list[ImpressionShareReport] = []
        for item in data.get("data", []):
            reports.append(ImpressionShareReport.model_validate(item))
        return reports

    def get(self, report_id: int) -> ImpressionShareReport:
        """Get a specific impression share report by ID.

        Args:
            report_id: The report ID.

        Returns:
            The impression share report.
        """
        data = self._request("GET", str(report_id))
        report_data = data.get("data", data)
        return ImpressionShareReport.model_validate(report_data)

    async def get_async(self, report_id: int) -> ImpressionShareReport:
        """Get a specific impression share report by ID asynchronously.

        Args:
            report_id: The report ID.

        Returns:
            The impression share report.
        """
        data = await self._request_async("GET", str(report_id))
        report_data = data.get("data", data)
        return ImpressionShareReport.model_validate(report_data)

    def create_impression_share(
        self,
        start_date: date,
        end_date: date,
        *,
        name: str = "impression_share_report",
        granularity: GranularityType = GranularityType.DAILY,
        date_range: ImpressionShareDateRange | None = None,
        country_codes: builtins.list[str] | None = None,
    ) -> ImpressionShareReport:
        """Create a new impression share report.

        The report is created asynchronously. Use `get()` or `wait_for_report()`
        to poll for completion.

        Args:
            start_date: Report start date (max 12 weeks ago).
            end_date: Report end date.
            name: Name for the report.
            granularity: DAILY or WEEKLY (WEEKLY requires date_range).
            date_range: Required for WEEKLY granularity (LAST_WEEK, LAST_2_WEEKS, LAST_4_WEEKS).
            country_codes: Optional list of country codes to filter by.

        Returns:
            The created report (check state for completion status).

        Example:
            Create a daily report::

                report = client.custom_reports.create_impression_share(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 7),
                )
        """
        request: dict[str, Any] = {
            "name": name,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "granularity": granularity.value,
        }

        if date_range:
            request["dateRange"] = date_range.value

        if country_codes:
            request["selector"] = {
                "conditions": [
                    {
                        "field": "countryOrRegion",
                        "operator": "IN",
                        "values": country_codes,
                    }
                ]
            }

        data = self._request("POST", "", json=request)
        report_data = data.get("data", data)
        return ImpressionShareReport.model_validate(report_data)

    async def create_impression_share_async(
        self,
        start_date: date,
        end_date: date,
        *,
        name: str = "impression_share_report",
        granularity: GranularityType = GranularityType.DAILY,
        date_range: ImpressionShareDateRange | None = None,
        country_codes: builtins.list[str] | None = None,
    ) -> ImpressionShareReport:
        """Create a new impression share report asynchronously.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            name: Name for the report.
            granularity: DAILY or WEEKLY.
            date_range: Required for WEEKLY granularity.
            country_codes: Optional list of country codes to filter by.

        Returns:
            The created report.
        """
        request: dict[str, Any] = {
            "name": name,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "granularity": granularity.value,
        }

        if date_range:
            request["dateRange"] = date_range.value

        if country_codes:
            request["selector"] = {
                "conditions": [
                    {
                        "field": "countryOrRegion",
                        "operator": "IN",
                        "values": country_codes,
                    }
                ]
            }

        data = await self._request_async("POST", "", json=request)
        report_data = data.get("data", data)
        return ImpressionShareReport.model_validate(report_data)

    def _download_csv(self, download_uri: str) -> builtins.list[ImpressionShareReportRow]:
        """Download and parse CSV data from the report.

        Args:
            download_uri: The URL to download the CSV from.

        Returns:
            List of parsed report rows.
        """
        try:
            response = self._http_client.get(download_uri)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to download report CSV: {e}") from e

        rows: builtins.list[ImpressionShareReportRow] = []
        reader = csv.DictReader(io.StringIO(response.text))

        for row_data in reader:
            # Parse the CSV row into our model
            parsed = ImpressionShareReportRow(
                date=row_data.get("date"),
                app_name=row_data.get("appName"),
                adam_id=row_data.get("adamId"),
                country_or_region=row_data.get("countryOrRegion"),
                search_term=row_data.get("searchTerm"),
                low_impression_share=float(row_data["lowImpressionShare"])
                if row_data.get("lowImpressionShare")
                else None,
                high_impression_share=float(row_data["highImpressionShare"])
                if row_data.get("highImpressionShare")
                else None,
                rank=row_data.get("rank"),
                search_popularity=int(row_data["searchPopularity"])
                if row_data.get("searchPopularity")
                else None,
            )
            rows.append(parsed)

        return rows

    async def _download_csv_async(
        self, download_uri: str
    ) -> builtins.list[ImpressionShareReportRow]:
        """Download and parse CSV data from the report asynchronously."""
        try:
            response = await self._async_http_client.get(download_uri)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to download report CSV: {e}") from e

        rows: builtins.list[ImpressionShareReportRow] = []
        reader = csv.DictReader(io.StringIO(response.text))

        for row_data in reader:
            parsed = ImpressionShareReportRow(
                date=row_data.get("date"),
                app_name=row_data.get("appName"),
                adam_id=row_data.get("adamId"),
                country_or_region=row_data.get("countryOrRegion"),
                search_term=row_data.get("searchTerm"),
                low_impression_share=float(row_data["lowImpressionShare"])
                if row_data.get("lowImpressionShare")
                else None,
                high_impression_share=float(row_data["highImpressionShare"])
                if row_data.get("highImpressionShare")
                else None,
                rank=row_data.get("rank"),
                search_popularity=int(row_data["searchPopularity"])
                if row_data.get("searchPopularity")
                else None,
            )
            rows.append(parsed)

        return rows

    def wait_for_report(
        self,
        report_id: int,
        *,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        download_data: bool = True,
    ) -> ImpressionShareReport:
        """Wait for a report to complete and optionally download data.

        Polls the report status until it's COMPLETED or FAILED.
        When complete, downloads and parses the CSV data.

        Args:
            report_id: The report ID to wait for.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait.
            download_data: Whether to download and parse CSV data.

        Returns:
            The completed report with data.

        Raises:
            TimeoutError: If the report doesn't complete within timeout.
            RuntimeError: If the report fails.
        """
        start_time = time.time()

        while True:
            report = self.get(report_id)

            if report.is_complete:
                if download_data and report.download_uri:
                    report.row = self._download_csv(report.download_uri)
                return report

            if report.is_failed:
                raise RuntimeError(f"Report {report_id} failed to generate")

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Report {report_id} did not complete within {timeout}s")

            logger.debug(f"Report {report_id} state: {report.state}, waiting {poll_interval}s...")
            time.sleep(poll_interval)

    async def wait_for_report_async(
        self,
        report_id: int,
        *,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        download_data: bool = True,
    ) -> ImpressionShareReport:
        """Wait for a report to complete asynchronously.

        Args:
            report_id: The report ID to wait for.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait.
            download_data: Whether to download and parse CSV data.

        Returns:
            The completed report with data.

        Raises:
            TimeoutError: If the report doesn't complete within timeout.
            RuntimeError: If the report fails.
        """
        import asyncio

        start_time = time.time()

        while True:
            report = await self.get_async(report_id)

            if report.is_complete:
                if download_data and report.download_uri:
                    report.row = await self._download_csv_async(report.download_uri)
                return report

            if report.is_failed:
                raise RuntimeError(f"Report {report_id} failed to generate")

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Report {report_id} did not complete within {timeout}s")

            logger.debug(f"Report {report_id} state: {report.state}, waiting {poll_interval}s...")
            await asyncio.sleep(poll_interval)

    def get_impression_share(
        self,
        start_date: date,
        end_date: date,
        *,
        name: str = "impression_share_report",
        granularity: GranularityType = GranularityType.DAILY,
        date_range: ImpressionShareDateRange | None = None,
        country_codes: builtins.list[str] | None = None,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> ImpressionShareReport:
        """Create an impression share report and wait for results.

        This is a convenience method that creates a report and polls
        until it's complete.

        Args:
            start_date: Report start date (max 12 weeks ago).
            end_date: Report end date.
            name: Name for the report.
            granularity: DAILY or WEEKLY.
            date_range: Required for WEEKLY granularity.
            country_codes: Optional list of country codes to filter by.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait.

        Returns:
            The completed report with impression share data.

        Example:
            Get impression share for last 7 days::

                from datetime import date, timedelta

                report = client.custom_reports.get_impression_share(
                    start_date=date.today() - timedelta(days=7),
                    end_date=date.today() - timedelta(days=1),
                )

                for row in report.row:
                    keyword = row.metadata.keyword
                    share = f"{row.low_impression_share}-{row.high_impression_share}%"
                    print(f"{keyword}: {share}")
        """
        report = self.create_impression_share(
            start_date=start_date,
            end_date=end_date,
            name=name,
            granularity=granularity,
            date_range=date_range,
            country_codes=country_codes,
        )

        return self.wait_for_report(
            report.id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

    async def get_impression_share_async(
        self,
        start_date: date,
        end_date: date,
        *,
        name: str = "impression_share_report",
        granularity: GranularityType = GranularityType.DAILY,
        date_range: ImpressionShareDateRange | None = None,
        country_codes: builtins.list[str] | None = None,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> ImpressionShareReport:
        """Create an impression share report and wait for results asynchronously.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            name: Name for the report.
            granularity: DAILY or WEEKLY.
            date_range: Required for WEEKLY granularity.
            country_codes: Optional list of country codes to filter by.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait.

        Returns:
            The completed report with impression share data.
        """
        report = await self.create_impression_share_async(
            start_date=start_date,
            end_date=end_date,
            name=name,
            granularity=granularity,
            date_range=date_range,
            country_codes=country_codes,
        )

        return await self.wait_for_report_async(
            report.id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

    def delete(self, report_id: int) -> None:
        """Delete an impression share report.

        Args:
            report_id: The report ID to delete.
        """
        self._request("DELETE", str(report_id))

    async def delete_async(self, report_id: int) -> None:
        """Delete an impression share report asynchronously.

        Args:
            report_id: The report ID to delete.
        """
        await self._request_async("DELETE", str(report_id))
