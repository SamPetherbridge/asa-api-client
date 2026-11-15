"""End-to-end CLI tests with a mocked transport."""

from pathlib import Path

import pytest
from openpyxl import load_workbook
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from asa_api_client.cli.analyze import app
from tests.unit.cli.conftest import TOKEN_URL, V1_API, mock_v1_api, token_json

runner = CliRunner()


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
class TestAnalyzeCommand:
    """asa analyze end to end."""

    @pytest.mark.usefixtures("asa_env")
    def test_happy_path(self, httpx_mock: HTTPXMock, tmp_path: Path) -> None:
        """Default run auto-selects account, writes workbook, prints headline."""
        mock_v1_api(httpx_mock)
        out = tmp_path / "report.xlsx"
        result = runner.invoke(app, ["analyze", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert str(out) in result.output
        assert "spend" in result.output and "installs" in result.output
        wb = load_workbook(out)
        assert wb.sheetnames[0] == "Summary"

    @pytest.mark.usefixtures("asa_env")
    def test_app_filter_and_default_name(
        self, httpx_mock: HTTPXMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--app scopes; default filename includes the adam id."""
        mock_v1_api(httpx_mock)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["analyze", "--app", "111"])
        assert result.exit_code == 0, result.output
        produced = list(tmp_path.glob("asa-analysis-111-*.xlsx"))
        assert len(produced) == 1

    @pytest.mark.usefixtures("asa_env")
    def test_ambiguous_accounts_clean_error(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple unmatched ACL accounts fail cleanly when ASA_AD_ACCOUNT_ID is unset."""
        monkeypatch.delenv("ASA_ORG_ID", raising=False)
        httpx_mock.add_response(url=TOKEN_URL, json=token_json(), is_reusable=True)
        httpx_mock.add_response(
            url=f"{V1_API}/acls",
            json={
                "result": {
                    "acls": [
                        {"adAccount": {"id": 100, "name": "Acct A"}, "roles": ["Admin"]},
                        {"adAccount": {"id": 200, "name": "Acct B"}, "roles": ["Admin"]},
                    ]
                }
            },
        )
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 1
        assert "ASA_AD_ACCOUNT_ID" in result.output

    @pytest.mark.usefixtures("asa_env")
    def test_invalid_range_fails_before_network(self, httpx_mock: HTTPXMock) -> None:
        """--from after --to exits non-zero with a clean message and no requests."""
        result = runner.invoke(app, ["analyze", "--from", "2026-05-02", "--to", "2026-05-01"])
        assert result.exit_code != 0
        assert "before" in (result.output + str(result.exception or ""))
        assert not httpx_mock.get_requests()

    def test_missing_credentials_clean_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No env vars → one-line configuration error, no traceback."""
        monkeypatch.chdir(tmp_path)
        for var in (
            "ASA_CLIENT_ID",
            "ASA_TEAM_ID",
            "ASA_KEY_ID",
            "ASA_ORG_ID",
            "ASA_AD_ACCOUNT_ID",
            "ASA_PRIVATE_KEY",
            "ASA_PRIVATE_KEY_PATH",
        ):
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 1
        assert result.exception is None or isinstance(result.exception, SystemExit)

    @pytest.mark.usefixtures("asa_env")
    def test_unwritable_output_clean_error(self, httpx_mock: HTTPXMock, tmp_path: Path) -> None:
        """A bad --output path fails cleanly, not with a raw traceback."""
        mock_v1_api(httpx_mock)
        bad = tmp_path / "does-not-exist" / "report.xlsx"
        result = runner.invoke(app, ["analyze", "--output", str(bad)])
        assert result.exit_code == 1
        assert "Could not write" in result.output
