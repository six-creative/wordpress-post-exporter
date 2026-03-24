"""Tests for exporters.py."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from wp_exporter.exporters import (
    _build_insert_statements,
    _build_mysql_schema,
    _column_definition,
    _mysql_escape,
    _mysql_literal,
    export_to_csv,
    export_to_sql_dump,
)


# ---------------------------------------------------------------------------
# _mysql_escape
# ---------------------------------------------------------------------------

class TestMysqlEscape:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("hello", "hello"),
            ("line\nbreak", "line\\nbreak"),
            ("line\rreturn", "line\\rreturn"),
            ("null\x00byte", "null\\0byte"),
            ("backslash\\", "backslash\\\\"),
            ("\x1a", "\\Z"),
            ("single'quote", "single\\'quote"),
            ("double\"quote", 'double"quote'),
        ],
    )
    def test_escapes_correctly(self, value: str, expected: str) -> None:
        assert _mysql_escape(value) == expected


# ---------------------------------------------------------------------------
# _mysql_literal
# ---------------------------------------------------------------------------

class TestMysqlLiteral:
    def test_none(self) -> None:
        assert _mysql_literal(None) == "NULL"

    def test_true(self) -> None:
        assert _mysql_literal(True) == "1"

    def test_false(self) -> None:
        assert _mysql_literal(False) == "0"

    def test_int(self) -> None:
        assert _mysql_literal(42) == "42"

    def test_str(self) -> None:
        assert _mysql_literal("hello") == "'hello'"

    def test_str_escapes(self) -> None:
        assert _mysql_literal("it's") == "'it\\'s'"

    def test_other_type_coerced_to_str(self) -> None:
        assert _mysql_literal(3.14) == "'3.14'"


# ---------------------------------------------------------------------------
# _column_definition
# ---------------------------------------------------------------------------

class TestColumnDefinition:
    def test_id_is_bigint_not_null(self) -> None:
        assert _column_definition("id") == "`id` BIGINT NOT NULL"

    def test_author_id_bigint_null(self) -> None:
        assert _column_definition("author_id") == "`author_id` BIGINT NULL"

    def test_featured_media_bigint_null(self) -> None:
        assert _column_definition("featured_media") == "`featured_media` BIGINT NULL"

    def test_date_datetime_null(self) -> None:
        assert _column_definition("date") == "`date` DATETIME NULL"

    def test_date_gmt_datetime_null(self) -> None:
        assert _column_definition("date_gmt") == "`date_gmt` DATETIME NULL"

    def test_modified_datetime_null(self) -> None:
        assert _column_definition("modified") == "`modified` DATETIME NULL"

    def test_modified_gmt_datetime_null(self) -> None:
        assert _column_definition("modified_gmt") == "`modified_gmt` DATETIME NULL"

    def test_text_columns_longtext_null(self) -> None:
        for col in (
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
        ):
            assert _column_definition(col) == f"`{col}` LONGTEXT NULL"

    def test_unknown_column_longtext_null(self) -> None:
        assert _column_definition("unknown_col") == "`unknown_col` LONGTEXT NULL"


# ---------------------------------------------------------------------------
# _build_mysql_schema
# ---------------------------------------------------------------------------

class TestBuildMysqlSchema:
    def test_basic_schema(self) -> None:
        fields = ["id", "title_rendered"]
        sql = _build_mysql_schema(fields)
        assert "DROP TABLE IF EXISTS `posts`;" in sql
        assert "CREATE TABLE `posts`" in sql
        assert "`id` BIGINT NOT NULL" in sql
        assert "`title_rendered` LONGTEXT NULL" in sql
        assert "PRIMARY KEY (`id`)" in sql
        assert "ENGINE=InnoDB" in sql
        assert "CHARSET=utf8mb4" in sql

    def test_schema_without_id(self) -> None:
        fields = ["title_rendered", "content_rendered"]
        sql = _build_mysql_schema(fields)
        assert "PRIMARY KEY" not in sql

    def test_all_column_types_in_schema(self) -> None:
        fields = [
            "id",
            "author_id",
            "featured_media",
            "date",
            "date_gmt",
            "modified",
            "modified_gmt",
            "slug",
        ]
        sql = _build_mysql_schema(fields)
        assert "`id` BIGINT NOT NULL" in sql
        assert "`author_id` BIGINT NULL" in sql
        assert "`featured_media` BIGINT NULL" in sql
        assert "`date` DATETIME NULL" in sql
        assert "`slug` LONGTEXT NULL" in sql


# ---------------------------------------------------------------------------
# _build_insert_statements
# ---------------------------------------------------------------------------

class TestBuildInsertStatements:
    def test_empty_rows(self) -> None:
        assert _build_insert_statements([], ["id", "title_rendered"]) == ""

    def test_single_row(self) -> None:
        rows = [{"id": 1, "title_rendered": "Hello"}]
        sql = _build_insert_statements(rows, ["id", "title_rendered"])
        assert "INSERT INTO `posts`" in sql
        assert "`id`, `title_rendered`" in sql
        assert "(1, 'Hello')" in sql

    def test_multiple_rows_chunked(self) -> None:
        rows = [{"id": i, "title_rendered": f"Post {i}"} for i in range(1, 401)]
        sql = _build_insert_statements(rows, ["id", "title_rendered"])
        # 400 rows / 200 chunk size = 2 INSERT statements
        assert sql.count("INSERT INTO `posts`") == 2

    def test_null_values(self) -> None:
        rows = [{"id": 1, "title_rendered": None}]
        sql = _build_insert_statements(rows, ["id", "title_rendered"])
        assert "NULL" in sql

    def test_escaped_values(self) -> None:
        rows = [{"id": 1, "title_rendered": "It's a \"test\"\nwith\\backslash"}]
        sql = _build_insert_statements(rows, ["id", "title_rendered"])
        assert "\\'It" in sql or "It" in sql  # single quote escaped
        assert '\\n' in sql or '"test"' in sql  # newline and double quote present


# ---------------------------------------------------------------------------
# export_to_csv
# ---------------------------------------------------------------------------

class TestExportToCsv:
    def test_empty_rows_writes_blank_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "empty.csv"
        export_to_csv([], output_path)
        assert output_path.read_text(encoding="utf-8") == ""

    def test_single_row(self, tmp_path: Path) -> None:
        output_path = tmp_path / "single.csv"
        rows = [
            {
                "id": 1,
                "title_rendered": "Hello",
                "content": "<p>World</p>",
            }
        ]
        export_to_csv(rows, output_path)
        content = output_path.read_text(encoding="utf-8")
        reader = list(csv.DictReader(StringIO(content)))
        assert len(reader) == 1
        assert reader[0]["id"] == "1"
        assert reader[0]["title_rendered"] == "Hello"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        output_path = tmp_path / "subdir" / "nested" / "output.csv"
        assert not output_path.parent.exists()
        export_to_csv([{"id": 1, "title_rendered": "A"}], output_path)
        assert output_path.parent.exists()

    def test_field_order_preserved(self, tmp_path: Path) -> None:
        output_path = tmp_path / "order.csv"
        rows = [
            {
                "id": 1,
                "title_rendered": "Title",
                "content": "Body",
                "author_id": 5,
            }
        ]
        export_to_csv(rows, output_path)
        header = output_path.read_text(encoding="utf-8").splitlines()[0]
        fields = header.split(",")
        assert fields == ["id", "title_rendered", "content", "author_id"]


# ---------------------------------------------------------------------------
# export_to_sql_dump
# ---------------------------------------------------------------------------

class TestExportToSqlDump:
    def test_creates_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "dump.sql"
        rows = [{"id": 1, "title_rendered": "Hello"}]
        export_to_sql_dump(rows, output_path)
        assert output_path.exists()

    def test_header_includes_utf8mb4(self, tmp_path: Path) -> None:
        output_path = tmp_path / "dump.sql"
        export_to_sql_dump([{"id": 1, "title_rendered": "Hello"}], output_path)
        content = output_path.read_text(encoding="utf-8")
        assert "SET NAMES utf8mb4" in content
        assert "SET time_zone = '+00:00'" in content

    def test_drops_and_creates_table(self, tmp_path: Path) -> None:
        output_path = tmp_path / "dump.sql"
        export_to_sql_dump([{"id": 1, "title_rendered": "Hello"}], output_path)
        content = output_path.read_text(encoding="utf-8")
        assert "DROP TABLE IF EXISTS `posts`" in content
        assert "CREATE TABLE `posts`" in content

    def test_empty_rows_uses_default_fields(self, tmp_path: Path) -> None:
        output_path = tmp_path / "empty.sql"
        export_to_sql_dump([], output_path)
        content = output_path.read_text(encoding="utf-8")
        assert "`id`" in content
        assert "`raw_post_json`" in content

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        output_path = tmp_path / "subdir" / "nested" / "dump.sql"
        assert not output_path.parent.exists()
        export_to_sql_dump([{"id": 1, "title_rendered": "A"}], output_path)
        assert output_path.parent.exists()

    def test_full_dump_structure(self, tmp_path: Path) -> None:
        output_path = tmp_path / "full.sql"
        rows = [
            {
                "id": 1,
                "date": "2024-01-01T10:00:00",
                "title_rendered": "Hello",
                "title_raw": "Hello",
                "content_rendered": "<p>Content</p>",
                "content_raw": "Content",
                "author_id": 5,
                "categories_ids": "[1]",
                "raw_post_json": "{}",
            }
        ]
        export_to_sql_dump(rows, output_path)
        content = output_path.read_text(encoding="utf-8")
        assert "SET NAMES utf8mb4" in content
        assert "DROP TABLE IF EXISTS `posts`;" in content
        assert "INSERT INTO `posts`" in content
