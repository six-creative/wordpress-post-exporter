"""Tests for main.py."""

from __future__ import annotations

import argparse
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wp_exporter import ExportConfig


class TestBuildParser:
    def test_required_base_url_and_output(self) -> None:
        from main import build_parser

        parser = build_parser()
        # Missing required args should fail
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_base_url_option(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--base-url", "https://example.com", "--output", "out.csv"])
        assert args.base_url == "https://example.com"

    def test_output_option(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--base-url", "https://example.com", "--output", "out.csv"])
        assert args.output == "out.csv"

    def test_format_csv_default(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--base-url", "https://example.com", "--output", "out.csv"])
        assert args.output_format == "csv"

    def test_format_sql(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["--base-url", "https://example.com", "--output", "out.sql", "--format", "sql"]
        )
        assert args.output_format == "sql"

    def test_format_invalid_rejected(self) -> None:
        from main import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["--base-url", "https://example.com", "--output", "out.xml", "--format", "xml"]
            )

    def test_token_option(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "--base-url", "https://example.com",
                "--output", "out.csv",
                "--token", "my-token",
            ]
        )
        assert args.token == "my-token"

    def test_username_option(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "--base-url", "https://example.com",
                "--output", "out.csv",
                "--username", "admin",
            ]
        )
        assert args.username == "admin"

    def test_application_password_option(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "--base-url", "https://example.com",
                "--output", "out.csv",
                "--application-password", "xxxx xxxx xxxx xxxx",
            ]
        )
        assert args.application_password == "xxxx xxxx xxxx xxxx"

    def test_timeout_default(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--base-url", "https://example.com", "--output", "out.csv"])
        assert args.timeout == 30

    def test_timeout_custom(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["--base-url", "https://example.com", "--output", "out.csv", "--timeout", "60"]
        )
        assert args.timeout == 60

    def test_quiet_flag(self) -> None:
        from main import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["--base-url", "https://example.com", "--output", "out.csv", "--quiet"]
        )
        assert args.quiet is True


class TestMain:
    @patch("main.export_posts")
    def test_success_returns_zero(self, mock_export: MagicMock) -> None:
        from main import main

        mock_export.return_value = 10

        with patch.object(sys, "argv", [
            "main.py",
            "--base-url", "https://example.com",
            "--output", "out.csv",
        ]):
            result = main()

        assert result == 0

    @patch("main.export_posts")
    def test_success_prints_output_path(self, mock_export: MagicMock) -> None:
        from main import main

        mock_export.return_value = 5

        stdout = StringIO()
        with patch.object(sys, "argv", [
            "main.py",
            "--base-url", "https://example.com",
            "--output", "out.csv",
        ]):
            with patch.object(sys, "stdout", stdout):
                main()

        output = stdout.getvalue()
        assert "out.csv" in output
        assert "5 posts" in output

    @patch("main.export_posts")
    def test_error_returns_one(self, mock_export: MagicMock) -> None:
        from main import main

        mock_export.side_effect = RuntimeError("test error")

        stderr = StringIO()
        with patch.object(sys, "argv", [
            "main.py",
            "--base-url", "https://example.com",
            "--output", "out.csv",
        ]):
            with patch.object(sys, "stderr", stderr):
                result = main()

        assert result == 1
        assert "test error" in stderr.getvalue()

    @patch("main.export_posts")
    def test_quiet_suppresses_info_messages(self, mock_export: MagicMock) -> None:
        from main import main

        mock_export.return_value = 1

        stdout = StringIO()
        with patch.object(sys, "argv", [
            "main.py",
            "--base-url", "https://example.com",
            "--output", "out.csv",
            "--quiet",
        ]):
            with patch.object(sys, "stdout", stdout):
                main()

        output = stdout.getvalue()
        assert "[INFO]" not in output

    @patch("main.export_posts")
    def test_config_passed_to_export_posts(self, mock_export: MagicMock) -> None:
        from main import main

        mock_export.return_value = 0

        with patch.object(sys, "argv", [
            "main.py",
            "--base-url", "https://example.com",
            "--output", "out.csv",
            "--format", "sql",
            "--token", "secret",
            "--timeout", "45",
        ]):
            main()

        config: ExportConfig = mock_export.call_args[0][0]
        assert config.base_url == "https://example.com"
        assert config.output_format == "sql"
        assert config.token == "secret"
        assert config.timeout_seconds == 45
