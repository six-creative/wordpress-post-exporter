from __future__ import annotations

from collections.abc import Callable
from typing import Any

import requests
from requests import HTTPError

from .config import ExportConfig


class WordPressClient:
    def __init__(
        self,
        config: ExportConfig,
        progress_reporter: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.progress_reporter = progress_reporter
        self.base_api_url = f"{config.normalized_base_url()}/wp-json/wp/v2"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if config.token:
            self.session.headers.update({"Authorization": f"Bearer {config.token}"})
        elif config.username and config.application_password:
            self.session.auth = (config.username, config.application_password)
        self.posts_context = "edit"

    @staticmethod
    def _is_auth_error(exc: HTTPError) -> bool:
        response = exc.response
        return response is not None and response.status_code in {401, 403}

    @staticmethod
    def _is_not_found_error(exc: HTTPError) -> bool:
        response = exc.response
        return response is not None and response.status_code == 404

    def _report(self, message: str) -> None:
        if self.progress_reporter is not None:
            self.progress_reporter(message)

    def _get_paginated(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        page = 1
        all_items: list[dict[str, Any]] = []
        current_params = dict(params or {})
        current_params["per_page"] = 100

        while True:
            current_params["page"] = page
            response = self.session.get(
                f"{self.base_api_url}/{endpoint}",
                params=current_params,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()

            items = response.json()
            total_pages = int(response.headers.get("X-WP-TotalPages", "1"))
            if not items:
                self._report(f"[{endpoint}] no records found.")
                break

            all_items.extend(items)
            self._report(
                f"[{endpoint}] page {page}/{total_pages} | "
                f"accumulated: {len(all_items)}"
            )
            if page >= total_pages:
                break
            page += 1

        return all_items

    def get_published_posts(self) -> list[dict[str, Any]]:
        params = {
            "status": "publish",
            "context": "edit",
            "_embed": "author,wp:term",
        }
        self._report("Fetching published posts (context=edit)...")
        try:
            posts = self._get_paginated(endpoint="posts", params=params)
            self.posts_context = "edit"
            return posts
        except HTTPError as exc:
            if not self._is_auth_error(exc):
                raise
            self._report(
                "No permission for context=edit. Falling back to public mode (context=view)."
            )

        fallback_params = {
            "status": "publish",
            "context": "view",
            "_embed": "author,wp:term",
        }
        posts = self._get_paginated(endpoint="posts", params=fallback_params)
        self.posts_context = "view"
        return posts

    def get_categories_map(self) -> dict[int, str]:
        self._report("Fetching categories...")
        try:
            categories = self._get_paginated(
                "categories", params={"context": self.posts_context}
            )
        except HTTPError as exc:
            if self._is_auth_error(exc) or self._is_not_found_error(exc):
                self._report(
                    "Categories unavailable in this context; continuing without category map."
                )
                return {}
            raise
        return {item["id"]: item.get("name", "") for item in categories}

    def get_tags_map(self) -> dict[int, str]:
        self._report("Fetching tags...")
        try:
            tags = self._get_paginated("tags", params={"context": self.posts_context})
        except HTTPError as exc:
            if self._is_auth_error(exc) or self._is_not_found_error(exc):
                self._report("Tags unavailable in this context; continuing without tag map.")
                return {}
            raise
        return {item["id"]: item.get("name", "") for item in tags}

    def get_users_map(self) -> dict[int, str]:
        self._report("Fetching authors...")
        try:
            users = self._get_paginated("users", params={"context": self.posts_context})
        except HTTPError as exc:
            if self._is_auth_error(exc) or self._is_not_found_error(exc):
                self._report(
                    "Users endpoint unavailable; using author data from _embedded."
                )
                return {}
            raise
        return {item["id"]: item.get("name", "") for item in users}
