from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wp_exporter import ExportConfig, export_posts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export published WordPress posts to CSV or MySQL SQL dump."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="WordPress site base URL (e.g. https://site.com)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["csv", "sql"],
        default="csv",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path (e.g. export.csv or export.sql)",
    )

    auth = parser.add_argument_group("Authentication")
    auth.add_argument("--token", help="Bearer token for the WordPress API")
    auth.add_argument(
        "--username", help="WordPress username (for Application Password)"
    )
    auth.add_argument("--application-password", help="WordPress Application Password")

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for each HTTP request.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable progress logs in the terminal.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = ExportConfig(
        base_url=args.base_url,
        output_path=Path(args.output),
        output_format=args.output_format,
        token=args.token,
        username=args.username,
        application_password=args.application_password,
        timeout_seconds=args.timeout,
    )

    def report_progress(message: str) -> None:
        if not args.quiet:
            print(f"[INFO] {message}", flush=True)

    try:
        total = export_posts(config, progress_reporter=report_progress)
    except Exception as exc:  # noqa: BLE001
        print(f"Error exporting posts: {exc}", file=sys.stderr)
        return 1

    print(f"Export completed. {total} posts written to: {config.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
