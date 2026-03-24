"""Shared fixtures for tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from wp_exporter import ExportConfig


@pytest.fixture
def sample_config(tmp_path: Path) -> ExportConfig:
    """Minimal ExportConfig for testing."""
    return ExportConfig(
        base_url="https://example.com",
        output_path=tmp_path / "output.csv",
        output_format="csv",
        token=None,
        username=None,
        application_password=None,
        timeout_seconds=30,
    )


@pytest.fixture
def sample_config_sql(tmp_path: Path) -> ExportConfig:
    """ExportConfig for SQL output testing."""
    return ExportConfig(
        base_url="https://example.com",
        output_path=tmp_path / "output.sql",
        output_format="sql",
        token="test-token",
        username=None,
        application_password=None,
        timeout_seconds=30,
    )


@pytest.fixture
def mock_progress_reporter() -> MagicMock:
    """Mock progress reporter that records calls."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Raw WordPress post fixtures (as returned by the REST API)
# ---------------------------------------------------------------------------

_MINIMAL_POST: dict[str, Any] = {
    "id": 1,
    "date": "2024-01-01T10:00:00",
    "date_gmt": "2024-01-01T10:00:00",
    "modified": "2024-01-02T12:00:00",
    "modified_gmt": "2024-01-02T12:00:00",
    "slug": "hello-world",
    "status": "publish",
    "type": "post",
    "link": "https://example.com/hello-world/",
    "title": {"rendered": "Hello World", "raw": "Hello World"},
    "excerpt": {"rendered": "<p>Excerpt text</p>", "raw": "Excerpt text"},
    "content": {"rendered": "<p>Post content here</p>", "raw": "Post content here"},
    "author": 5,
    "categories": [1, 2],
    "tags": [10, 20],
    "featured_media": 7,
    "comment_status": "open",
    "ping_status": "closed",
    "template": "",
    "format": "standard",
    "meta": {"foo": "bar"},
    "_embedded": {
        "author": [{"id": 5, "name": "John Doe"}],
        "wp:term": [
            [
                {"id": 1, "name": "Tech", "taxonomy": "category"},
                {"id": 2, "name": "News", "taxonomy": "category"},
            ],
            [
                {"id": 10, "name": "Python", "taxonomy": "post_tag"},
                {"id": 20, "name": "WordPress", "taxonomy": "post_tag"},
            ],
        ],
    },
}


@pytest.fixture
def minimal_post() -> dict[str, Any]:
    """Minimal valid WordPress post dict."""
    return _MINIMAL_POST.copy()


@pytest.fixture
def post_with_missing_fields() -> dict[str, Any]:
    """Post with several fields missing / malformed."""
    return {
        "id": 2,
        "slug": "incomplete",
        "_embedded": {},
    }


@pytest.fixture
def post_no_title_raw() -> dict[str, Any]:
    """Post where title has no 'raw' field (common in public context)."""
    return {
        "id": 3,
        "date": "2024-03-01T00:00:00",
        "date_gmt": "2024-03-01T00:00:00",
        "modified": "",
        "modified_gmt": "",
        "slug": "no-raw",
        "status": "publish",
        "type": "post",
        "link": "https://example.com/no-raw/",
        "title": {"rendered": "No Raw Title"},
        "excerpt": {"rendered": ""},
        "content": {"rendered": "Content only rendered"},
        "author": 1,
        "categories": [],
        "tags": [],
        "featured_media": 0,
        "comment_status": "closed",
        "ping_status": "closed",
        "template": "",
        "format": "aside",
        "meta": {},
        "_embedded": {
            "author": [{"id": 1, "name": "Jane Doe"}],
            "wp:term": [],
        },
    }


@pytest.fixture
def post_empty_lists() -> dict[str, Any]:
    """Post with empty categories and tags (and no embedded fallback data)."""
    return {
        "id": 4,
        "date": "2024-01-01T10:00:00",
        "date_gmt": "2024-01-01T10:00:00",
        "modified": "",
        "modified_gmt": "",
        "slug": "empty-lists",
        "status": "publish",
        "type": "post",
        "link": "https://example.com/empty-lists/",
        "title": {"rendered": "Empty Lists Post"},
        "excerpt": {"rendered": ""},
        "content": {"rendered": "Content"},
        "author": 1,
        "categories": [],
        "tags": [],
        "featured_media": 0,
        "comment_status": "closed",
        "ping_status": "closed",
        "template": "",
        "format": "standard",
        "meta": {},
        "_embedded": {
            "author": [{"id": 1, "name": "Jane Doe"}],
            "wp:term": [],
        },
    }


# ---------------------------------------------------------------------------
# Normalized row fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def normalized_row() -> dict[str, Any]:
    """Expected normalized row for the minimal post fixture."""
    import json

    post = _MINIMAL_POST
    return {
        "id": post["id"],
        "date": post["date"],
        "date_gmt": post["date_gmt"],
        "modified": post["modified"],
        "modified_gmt": post["modified_gmt"],
        "slug": post["slug"],
        "status": post["status"],
        "type": post["type"],
        "link": post["link"],
        "title_rendered": "Hello World",
        "title_raw": "Hello World",
        "excerpt_rendered": "<p>Excerpt text</p>",
        "excerpt_raw": "Excerpt text",
        "content_rendered": "<p>Post content here</p>",
        "content_raw": "Post content here",
        "author_id": 5,
        "author_name": "John Doe",
        "categories_ids": json.dumps([1, 2]),
        "categories_names": json.dumps(["Tech", "News"]),
        "tags_ids": json.dumps([10, 20]),
        "tags_names": json.dumps(["Python", "WordPress"]),
        "featured_media": 7,
        "comment_status": "open",
        "ping_status": "closed",
        "template": "",
        "format": "standard",
        "meta": json.dumps({"foo": "bar"}),
        "raw_post_json": json.dumps(post),
    }


# ---------------------------------------------------------------------------
# Helper to build paginated response objects
# ---------------------------------------------------------------------------


def build_response(
    json_data: list[dict[str, Any]],
    total_pages: int = 1,
    status_code: int = 200,
) -> MagicMock:
    """Build a mock response for requests.Session.get."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.headers = {"X-WP-TotalPages": str(total_pages)}
    resp.raise_for_status = MagicMock()
    return resp
