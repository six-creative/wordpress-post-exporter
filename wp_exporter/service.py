from __future__ import annotations

from collections.abc import Callable

from .client import WordPressClient
from .config import ExportConfig
from .exporters import export_to_csv, export_to_sql_dump
from .transformers import normalize_post


def _report(progress_reporter: Callable[[str], None] | None, message: str) -> None:
    if progress_reporter is not None:
        progress_reporter(message)


def export_posts(
    config: ExportConfig,
    progress_reporter: Callable[[str], None] | None = None,
) -> int:
    config.validate()
    _report(progress_reporter, "Starting export...")

    client = WordPressClient(config, progress_reporter=progress_reporter)
    posts = client.get_published_posts()
    categories_map = client.get_categories_map()
    tags_map = client.get_tags_map()
    users_map = client.get_users_map()
    _report(progress_reporter, f"Total posts found: {len(posts)}")

    _report(progress_reporter, "Normalizing data...")
    normalized_rows = []
    total_posts = len(posts)
    for idx, post in enumerate(posts, start=1):
        normalized_rows.append(
            normalize_post(
                post,
                categories_map=categories_map,
                tags_map=tags_map,
                users_map=users_map,
            )
        )
        if idx % 200 == 0 or idx == total_posts:
            _report(progress_reporter, f"Normalized: {idx}/{total_posts}")

    if config.output_format == "csv":
        _report(progress_reporter, f"Writing CSV file to {config.output_path}...")
        export_to_csv(normalized_rows, config.output_path)
    elif config.output_format == "sql":
        _report(progress_reporter, f"Writing SQL file to {config.output_path}...")
        export_to_sql_dump(normalized_rows, config.output_path)
    else:
        raise ValueError(f"Unsupported format: {config.output_format}")

    return len(normalized_rows)
