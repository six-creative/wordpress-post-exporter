from __future__ import annotations

import csv
import sqlite3
import tempfile
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


def export_to_sql_dump(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
        conn = sqlite3.connect(temp_db.name)
        try:
            if rows:
                fields = list(rows[0].keys())
                column_defs = []
                for field in fields:
                    field_type = "INTEGER" if field in {"id", "author_id", "featured_media"} else "TEXT"
                    column_defs.append(f'"{field}" {field_type}')

                conn.execute(f'CREATE TABLE posts ({", ".join(column_defs)});')

                placeholders = ", ".join(["?"] * len(fields))
                quoted_fields = ", ".join(f'"{field}"' for field in fields)
                insert_sql = f"INSERT INTO posts ({quoted_fields}) VALUES ({placeholders});"
                values = [[row.get(field) for field in fields] for row in rows]
                conn.executemany(insert_sql, values)
                conn.commit()
            else:
                conn.execute('CREATE TABLE posts (id INTEGER, raw_post_json TEXT);')
                conn.commit()

            dump = "\n".join(conn.iterdump()) + "\n"
            output_path.write_text(dump, encoding="utf-8")
        finally:
            conn.close()
