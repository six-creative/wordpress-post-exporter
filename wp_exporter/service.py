from __future__ import annotations

from .client import WordPressClient
from .config import ExportConfig
from .exporters import export_to_csv, export_to_sql_dump
from .transformers import normalize_post


def export_posts(config: ExportConfig) -> int:
    config.validate()

    client = WordPressClient(config)
    posts = client.get_published_posts()
    categories_map = client.get_categories_map()
    tags_map = client.get_tags_map()
    users_map = client.get_users_map()

    normalized_rows = [
        normalize_post(post, categories_map=categories_map, tags_map=tags_map, users_map=users_map)
        for post in posts
    ]

    if config.output_format == "csv":
        export_to_csv(normalized_rows, config.output_path)
    elif config.output_format == "sql":
        export_to_sql_dump(normalized_rows, config.output_path)
    else:
        raise ValueError(f"Formato não suportado: {config.output_format}")

    return len(normalized_rows)
