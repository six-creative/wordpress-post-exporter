from __future__ import annotations

import json
from typing import Any


def _rendered(field: Any) -> str:
    if isinstance(field, dict):
        value = field.get("rendered")
        return value if isinstance(value, str) else ""
    return ""


def _raw(field: Any) -> str:
    if isinstance(field, dict):
        value = field.get("raw")
        return value if isinstance(value, str) else ""
    return ""


def _embedded_author_name(post: dict[str, Any]) -> str:
    embedded = post.get("_embedded", {})
    authors = embedded.get("author", []) if isinstance(embedded, dict) else []
    if authors and isinstance(authors[0], dict):
        name = authors[0].get("name", "")
        return name if isinstance(name, str) else ""
    return ""


def _embedded_terms(post: dict[str, Any]) -> tuple[list[str], list[str]]:
    embedded = post.get("_embedded", {})
    term_groups = embedded.get("wp:term", []) if isinstance(embedded, dict) else []
    category_names: list[str] = []
    tag_names: list[str] = []

    for group in term_groups:
        if not isinstance(group, list):
            continue
        for term in group:
            if not isinstance(term, dict):
                continue
            term_name = term.get("name", "")
            taxonomy = term.get("taxonomy", "")
            if not isinstance(term_name, str):
                continue
            if taxonomy == "category":
                category_names.append(term_name)
            elif taxonomy == "post_tag":
                tag_names.append(term_name)

    return category_names, tag_names


def normalize_post(
    post: dict[str, Any],
    categories_map: dict[int, str],
    tags_map: dict[int, str],
    users_map: dict[int, str],
) -> dict[str, Any]:
    category_ids = post.get("categories", [])
    tag_ids = post.get("tags", [])
    author_id = post.get("author")
    embedded_category_names, embedded_tag_names = _embedded_terms(post)

    category_names = [categories_map.get(cid, "") for cid in category_ids]
    tag_names = [tags_map.get(tid, "") for tid in tag_ids]
    if not any(category_names):
        category_names = embedded_category_names
    if not any(tag_names):
        tag_names = embedded_tag_names

    author_name = users_map.get(author_id, "")
    if not author_name:
        author_name = _embedded_author_name(post)

    return {
        "id": post.get("id"),
        "date": post.get("date", ""),
        "date_gmt": post.get("date_gmt", ""),
        "modified": post.get("modified", ""),
        "modified_gmt": post.get("modified_gmt", ""),
        "slug": post.get("slug", ""),
        "status": post.get("status", ""),
        "type": post.get("type", ""),
        "link": post.get("link", ""),
        "title_rendered": _rendered(post.get("title")),
        "title_raw": _raw(post.get("title")),
        "excerpt_rendered": _rendered(post.get("excerpt")),
        "excerpt_raw": _raw(post.get("excerpt")),
        "content_rendered": _rendered(post.get("content")),
        "content_raw": _raw(post.get("content")),
        "author_id": author_id,
        "author_name": author_name,
        "categories_ids": json.dumps(category_ids, ensure_ascii=False),
        "categories_names": json.dumps(category_names, ensure_ascii=False),
        "tags_ids": json.dumps(tag_ids, ensure_ascii=False),
        "tags_names": json.dumps(tag_names, ensure_ascii=False),
        "featured_media": post.get("featured_media"),
        "comment_status": post.get("comment_status", ""),
        "ping_status": post.get("ping_status", ""),
        "template": post.get("template", ""),
        "format": post.get("format", ""),
        "meta": json.dumps(post.get("meta", {}), ensure_ascii=False),
        "raw_post_json": json.dumps(post, ensure_ascii=False),
    }
