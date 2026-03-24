"""Tests for transformers.py."""

from __future__ import annotations

import json

import pytest

from wp_exporter.transformers import (
    _embedded_author_name,
    _embedded_terms,
    _raw,
    _rendered,
    normalize_post,
)


class TestRendered:
    def test_dict_with_rendered_returns_string(self) -> None:
        assert _rendered({"rendered": "Hello"}) == "Hello"

    def test_dict_without_rendered_returns_empty(self) -> None:
        assert _rendered({}) == ""

    def test_dict_with_non_string_rendered_returns_empty(self) -> None:
        assert _rendered({"rendered": 123}) == ""

    def test_non_dict_returns_empty(self) -> None:
        assert _rendered("not a dict") == ""
        assert _rendered(None) == ""


class TestRaw:
    def test_dict_with_raw_returns_string(self) -> None:
        assert _raw({"raw": "Hello"}) == "Hello"

    def test_dict_without_raw_returns_empty(self) -> None:
        assert _raw({}) == ""

    def test_dict_with_non_string_raw_returns_empty(self) -> None:
        assert _raw({"raw": ["list"]}) == ""

    def test_non_dict_returns_empty(self) -> None:
        assert _raw(42) == ""


class TestEmbeddedAuthorName:
    def test_valid_embedded_author(self, minimal_post: dict) -> None:
        assert _embedded_author_name(minimal_post) == "John Doe"

    def test_no_embedded(self) -> None:
        post = {"_embedded": {}}
        assert _embedded_author_name(post) == ""

    def test_no_author_in_embedded(self) -> None:
        post = {"_embedded": {"author": []}}
        assert _embedded_author_name(post) == ""

    def test_author_is_not_dict(self) -> None:
        post = {"_embedded": {"author": ["not a dict"]}}
        assert _embedded_author_name(post) == ""

    def test_author_name_not_string(self) -> None:
        post = {"_embedded": {"author": [{"name": 123}]}}
        assert _embedded_author_name(post) == ""

    def test_embedded_is_not_dict(self) -> None:
        post = {"_embedded": "bad"}
        assert _embedded_author_name(post) == ""

    def test_no_embedded_at_all(self) -> None:
        post = {}
        assert _embedded_author_name(post) == ""


class TestEmbeddedTerms:
    def test_valid_terms(self, minimal_post: dict) -> None:
        cats, tags = _embedded_terms(minimal_post)
        assert cats == ["Tech", "News"]
        assert tags == ["Python", "WordPress"]

    def test_empty_embedded(self) -> None:
        cats, tags = _embedded_terms({})
        assert cats == []
        assert tags == []

    def test_empty_term_groups(self) -> None:
        post = {"_embedded": {"wp:term": []}}
        cats, tags = _embedded_terms(post)
        assert cats == []
        assert tags == []

    def test_term_group_not_list(self) -> None:
        post = {"_embedded": {"wp:term": "bad"}}
        cats, tags = _embedded_terms(post)
        assert cats == []
        assert tags == []

    def test_term_not_dict(self) -> None:
        post = {"_embedded": {"wp:term": [["not a dict"]]}}
        cats, tags = _embedded_terms(post)
        assert cats == []
        assert tags == []

    def test_term_name_not_string(self) -> None:
        post = {
            "_embedded": {
                "wp:term": [
                    [{"id": 1, "name": 999, "taxonomy": "category"}]
                ]
            }
        }
        cats, tags = _embedded_terms(post)
        assert cats == []

    def test_unknown_taxonomy(self) -> None:
        post = {
            "_embedded": {
                "wp:term": [
                    [{"id": 1, "name": "Unknown", "taxonomy": "custom_tax"}]
                ]
            }
        }
        cats, tags = _embedded_terms(post)
        assert cats == []
        assert tags == []

    def test_embedded_is_not_dict(self) -> None:
        post = {"_embedded": 123}
        cats, tags = _embedded_terms(post)
        assert cats == []
        assert tags == []


class TestNormalizePost:
    def test_basic_fields_extracted(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={1: "Tech", 2: "News"},
            tags_map={10: "Python", 20: "WordPress"},
            users_map={5: "John Doe"},
        )
        assert result["id"] == 1
        assert result["slug"] == "hello-world"
        assert result["status"] == "publish"
        assert result["type"] == "post"
        assert result["link"] == "https://example.com/hello-world/"

    def test_rendered_and_raw_fields(self, minimal_post: dict) -> None:
        result = normalize_post(minimal_post, {}, {}, {})
        assert result["title_rendered"] == "Hello World"
        assert result["title_raw"] == "Hello World"
        assert result["excerpt_rendered"] == "<p>Excerpt text</p>"
        assert result["excerpt_raw"] == "Excerpt text"
        assert result["content_rendered"] == "<p>Post content here</p>"
        assert result["content_raw"] == "Post content here"

    def test_author_from_users_map(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={},
            tags_map={},
            users_map={5: "John Doe"},
        )
        assert result["author_id"] == 5
        assert result["author_name"] == "John Doe"

    def test_author_from_embedded_when_not_in_map(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={},
            tags_map={},
            users_map={},
        )
        assert result["author_name"] == "John Doe"

    def test_categories_names_from_map(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={1: "Mapped Tech", 2: "Mapped News"},
            tags_map={},
            users_map={},
        )
        assert json.loads(result["categories_names"]) == ["Mapped Tech", "Mapped News"]

    def test_categories_names_fallback_to_embedded(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={},
            tags_map={},
            users_map={},
        )
        assert json.loads(result["categories_names"]) == ["Tech", "News"]

    def test_tags_names_from_map(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={},
            tags_map={10: "Mapped Python", 20: "Mapped WP"},
            users_map={},
        )
        assert json.loads(result["tags_names"]) == ["Mapped Python", "Mapped WP"]

    def test_tags_names_fallback_to_embedded(self, minimal_post: dict) -> None:
        result = normalize_post(
            minimal_post,
            categories_map={},
            tags_map={},
            users_map={},
        )
        assert json.loads(result["tags_names"]) == ["Python", "WordPress"]

    def test_categories_ids_json_serialized(self, minimal_post: dict) -> None:
        result = normalize_post(minimal_post, {}, {}, {})
        assert json.loads(result["categories_ids"]) == [1, 2]

    def test_tags_ids_json_serialized(self, minimal_post: dict) -> None:
        result = normalize_post(minimal_post, {}, {}, {})
        assert json.loads(result["tags_ids"]) == [10, 20]

    def test_meta_json_serialized(self, minimal_post: dict) -> None:
        result = normalize_post(minimal_post, {}, {}, {})
        assert json.loads(result["meta"]) == {"foo": "bar"}

    def test_raw_post_json_contains_full_post(self, minimal_post: dict) -> None:
        result = normalize_post(minimal_post, {}, {}, {})
        assert json.loads(result["raw_post_json"]) == minimal_post

    def test_missing_title(self) -> None:
        post = {"id": 1}
        result = normalize_post(post, {}, {}, {})
        assert result["title_rendered"] == ""
        assert result["title_raw"] == ""

    def test_missing_excerpt(self) -> None:
        post = {"id": 1}
        result = normalize_post(post, {}, {}, {})
        assert result["excerpt_rendered"] == ""
        assert result["excerpt_raw"] == ""

    def test_missing_content(self) -> None:
        post = {"id": 1}
        result = normalize_post(post, {}, {}, {})
        assert result["content_rendered"] == ""
        assert result["content_raw"] == ""

    def test_missing_author(self) -> None:
        post = {"id": 1}
        result = normalize_post(post, {}, {}, {})
        assert result["author_id"] is None
        assert result["author_name"] == ""

    def test_empty_string_dates(self) -> None:
        post = {"id": 1}
        result = normalize_post(post, {}, {}, {})
        assert result["date"] == ""
        assert result["date_gmt"] == ""
        assert result["modified"] == ""
        assert result["modified_gmt"] == ""

    def test_post_no_title_raw(self, post_no_title_raw: dict) -> None:
        result = normalize_post(post_no_title_raw, {}, {}, {})
        assert result["title_rendered"] == "No Raw Title"
        assert result["title_raw"] == ""

    def test_post_with_missing_fields(self, post_with_missing_fields: dict) -> None:
        result = normalize_post(post_with_missing_fields, {}, {}, {})
        assert result["id"] == 2
        assert result["slug"] == "incomplete"
        assert result["author_name"] == ""

    def test_post_empty_lists(self, post_empty_lists: dict) -> None:
        result = normalize_post(post_empty_lists, {}, {}, {})
        assert json.loads(result["categories_ids"]) == []
        assert json.loads(result["categories_names"]) == []
        assert json.loads(result["tags_ids"]) == []
        assert json.loads(result["tags_names"]) == []

    def test_categories_map_returns_unknown_as_empty_string(
        self, minimal_post: dict
    ) -> None:
        # When categories_map has unknown IDs (returning "" via get(cid, "")),
        # any(["", ""]) is False, so embedded categories are used as fallback
        result = normalize_post(
            minimal_post,
            categories_map={999: "Unknown"},
            tags_map={},
            users_map={},
        )
        # Unknown IDs get "" from the map, but any(["",""]) is False so embedded is used
        assert json.loads(result["categories_names"]) == ["Tech", "News"]

    def test_meta_default_empty_dict(self) -> None:
        post = {"id": 1}
        result = normalize_post(post, {}, {}, {})
        assert json.loads(result["meta"]) == {}

    def test_result_has_all_28_columns(self, minimal_post: dict) -> None:
        result = normalize_post(minimal_post, {}, {}, {})
        expected_keys = [
            "id",
            "date",
            "date_gmt",
            "modified",
            "modified_gmt",
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
            "author_id",
            "author_name",
            "categories_ids",
            "categories_names",
            "tags_ids",
            "tags_names",
            "featured_media",
            "comment_status",
            "ping_status",
            "template",
            "format",
            "meta",
            "raw_post_json",
        ]
        assert list(result.keys()) == expected_keys
