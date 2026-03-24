"""Tests for service.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from wp_exporter import ExportConfig, export_posts


def _report_calls(progress_reporter: MagicMock) -> list[str]:
    return [str(call) for call in progress_reporter.call_args_list]


class TestReport:
    def test_report_calls_reporter(self) -> None:
        from wp_exporter.service import _report
        reporter = MagicMock()
        _report(reporter, "hello")
        reporter.assert_called_once_with("hello")

    def test_report_does_nothing_when_none(self) -> None:
        from wp_exporter.service import _report
        _report(None, "hello")  # should not raise


class TestExportPosts:
    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_csv")
    def test_csv_export_flow(
        self,
        mock_csv: MagicMock,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = [{"id": 1, "slug": "a"}]
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client

        total = export_posts(sample_config, progress_reporter=mock_progress_reporter)

        assert total == 1
        mock_csv.assert_called_once()
        assert "Starting export" in str(mock_progress_reporter.call_args_list)

    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_sql_dump")
    def test_sql_export_flow(
        self,
        mock_sql: MagicMock,
        mock_client_class: MagicMock,
        sample_config_sql: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = [{"id": 1}]
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client

        total = export_posts(sample_config_sql, progress_reporter=mock_progress_reporter)

        assert total == 1
        mock_sql.assert_called_once()

    @patch("wp_exporter.service.WordPressClient")
    def test_validates_config(
        self,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        sample_config.output_format = "invalid"
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="output_format must be 'csv' or 'sql'"):
            export_posts(sample_config)

    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_csv")
    def test_progress_reported_at_each_step(
        self,
        mock_csv: MagicMock,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = []
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client

        export_posts(sample_config, progress_reporter=mock_progress_reporter)

        calls_as_str = str(mock_progress_reporter.call_args_list)
        assert "Starting export" in calls_as_str
        assert "Total posts found: 0" in calls_as_str
        assert "Normalizing data" in calls_as_str
        assert "Writing CSV file" in calls_as_str

    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_csv")
    def test_normalize_progress_reported_every_200(
        self,
        mock_csv: MagicMock,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        posts = [{"id": i, "slug": f"post-{i}"} for i in range(1, 401)]
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = posts
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client

        export_posts(sample_config, progress_reporter=mock_progress_reporter)

        # Progress is reported at 200 and 400
        calls_as_str = str(mock_progress_reporter.call_args_list)
        assert "Normalized: 200/400" in calls_as_str
        assert "Normalized: 400/400" in calls_as_str

    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_csv")
    def test_empty_posts(
        self,
        mock_csv: MagicMock,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = []
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client

        total = export_posts(sample_config, progress_reporter=mock_progress_reporter)

        assert total == 0
        mock_csv.assert_called_once_with([], sample_config.output_path)

    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_csv")
    def test_unsupported_format_raises(
        self,
        mock_csv: MagicMock,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = [{"id": 1}]
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client
        sample_config.output_format = "xml"

        with pytest.raises(ValueError, match="output_format must be 'csv' or 'sql'"):
            export_posts(sample_config)

    @patch("wp_exporter.service.WordPressClient")
    @patch("wp_exporter.service.export_to_csv")
    def test_without_progress_reporter(
        self,
        mock_csv: MagicMock,
        mock_client_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_client = MagicMock()
        mock_client.get_published_posts.return_value = [{"id": 1}]
        mock_client.get_categories_map.return_value = {}
        mock_client.get_tags_map.return_value = {}
        mock_client.get_users_map.return_value = {}
        mock_client_class.return_value = mock_client

        # Should not raise
        total = export_posts(sample_config, progress_reporter=None)
        assert total == 1
