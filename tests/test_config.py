"""Tests for config.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from wp_exporter import ExportConfig


class TestExportConfig:
    def test_required_fields(self) -> None:
        config = ExportConfig(
            base_url="https://example.com",
            output_path=Path("out.csv"),
            output_format="csv",
        )
        assert config.base_url == "https://example.com"
        assert config.output_path == Path("out.csv")
        assert config.output_format == "csv"
        assert config.token is None
        assert config.username is None
        assert config.application_password is None
        assert config.timeout_seconds == 30

    def test_all_fields(self) -> None:
        config = ExportConfig(
            base_url="https://example.com",
            output_path=Path("out.csv"),
            output_format="sql",
            token="my-token",
            username="admin",
            application_password="app-pass",
            timeout_seconds=60,
        )
        assert config.token == "my-token"
        assert config.username == "admin"
        assert config.application_password == "app-pass"
        assert config.timeout_seconds == 60

    def test_normalized_base_url_trailing_slash(self) -> None:
        config = ExportConfig(
            base_url="https://example.com/",
            output_path=Path("out.csv"),
            output_format="csv",
        )
        assert config.normalized_base_url() == "https://example.com"

    def test_normalized_base_url_no_trailing_slash(self) -> None:
        config = ExportConfig(
            base_url="https://example.com",
            output_path=Path("out.csv"),
            output_format="csv",
        )
        assert config.normalized_base_url() == "https://example.com"

    def test_normalized_base_url_multiple_slashes(self) -> None:
        config = ExportConfig(
            base_url="https://example.com///",
            output_path=Path("out.csv"),
            output_format="csv",
        )
        assert config.normalized_base_url() == "https://example.com"


class TestExportConfigValidate:
    def test_valid_csv_format(self, sample_config: ExportConfig) -> None:
        sample_config.validate()  # should not raise

    def test_valid_sql_format(self, sample_config_sql: ExportConfig) -> None:
        sample_config_sql.validate()  # should not raise

    def test_invalid_format_raises(self, sample_config: ExportConfig) -> None:
        sample_config.output_format = "xml"
        with pytest.raises(ValueError, match="output_format must be 'csv' or 'sql'"):
            sample_config.validate()
