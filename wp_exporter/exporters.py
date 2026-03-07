from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def export_to_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


INT_COLUMNS = {"id", "author_id", "featured_media"}

MYSQL_TEXT_COLUMNS = {
    "slug",
    "status",
    "type",
    "link",
    "title_rendered",
    "title_raw",
    "excerpt_rendered",
    "excerpt_raw",
    "content_rendered",
    "content_raw",
    "author_name",
    "categories_ids",
    "categories_names",
    "tags_ids",
    "tags_names",
    "comment_status",
    "ping_status",
    "template",
    "format",
    "meta",
    "raw_post_json",
}

MYSQL_DATETIME_COLUMNS = {"date", "date_gmt", "modified", "modified_gmt"}


def _mysql_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\x00", "\\0")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\x1a", "\\Z")
        .replace("'", "\\'")
    )


def _mysql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)

    text = str(value)
    return f"'{_mysql_escape(text)}'"


def _column_definition(column_name: str) -> str:
    if column_name == "id":
        return "`id` BIGINT NOT NULL"
    if column_name in INT_COLUMNS:
        return f"`{column_name}` BIGINT NULL"
    if column_name in MYSQL_DATETIME_COLUMNS:
        return f"`{column_name}` DATETIME NULL"
    if column_name in MYSQL_TEXT_COLUMNS:
        return f"`{column_name}` LONGTEXT NULL"
    return f"`{column_name}` LONGTEXT NULL"


def _build_mysql_schema(fields: list[str]) -> str:
    column_defs = [_column_definition(field) for field in fields]
    if "id" in fields:
        column_defs.append("PRIMARY KEY (`id`)")
    columns_sql = ",\n  ".join(column_defs)
    return (
        "DROP TABLE IF EXISTS `posts`;\n"
        "CREATE TABLE `posts` (\n"
        f"  {columns_sql}\n"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n"
    )


def _build_insert_statements(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return ""

    quoted_fields = ", ".join(f"`{field}`" for field in fields)
    statements: list[str] = []
    chunk_size = 200

    for offset in range(0, len(rows), chunk_size):
        chunk = rows[offset : offset + chunk_size]
        values_sql = []
        for row in chunk:
            values = ", ".join(_mysql_literal(row.get(field)) for field in fields)
            values_sql.append(f"({values})")

        statements.append(
            f"INSERT INTO `posts` ({quoted_fields}) VALUES\n"
            + ",\n".join(values_sql)
            + ";"
        )

    return "\n\n".join(statements) + "\n"


def export_to_sql_dump(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = list(rows[0].keys()) if rows else ["id", "raw_post_json"]
    header = (
        "-- WordPress posts dump (MySQL 8 compatible)\n"
        "SET NAMES utf8mb4;\n"
        "SET time_zone = '+00:00';\n\n"
    )
    schema_sql = _build_mysql_schema(fields)
    inserts_sql = _build_insert_statements(rows, fields)
    output_path.write_text(header + schema_sql + "\n" + inserts_sql, encoding="utf-8")
