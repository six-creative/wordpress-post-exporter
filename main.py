from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wp_exporter import ExportConfig, export_posts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta posts publicados do WordPress "
        "para CSV ou SQL dump (SQLite)."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="URL base do site WordPress (ex: https://site.com)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["csv", "sql"],
        default="csv",
        help="Formato de saída.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Caminho do arquivo de saída (ex: export.csv ou export.sql)",
    )

    auth = parser.add_argument_group("Autenticação")
    auth.add_argument("--token", help="Token Bearer para API do WordPress")
    auth.add_argument(
        "--username", help="Usuário WordPress (para Application Password)"
    )
    auth.add_argument(
        "--application-password", help="Application Password do WordPress"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout em segundos para cada chamada HTTP.",
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

    try:
        total = export_posts(config)
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao exportar posts: {exc}", file=sys.stderr)
        return 1

    print(f"Exportação concluída. {total} posts salvos em: {config.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
