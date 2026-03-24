"""Tests for client.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from requests import HTTPError

from wp_exporter import ExportConfig
from wp_exporter.client import WordPressClient


def _make_client(
    config: ExportConfig,
    progress_reporter: MagicMock | None = None,
) -> WordPressClient:
    return WordPressClient(config, progress_reporter=progress_reporter)


class TestWordPressClientInit:
    def test_base_url_normalized(self, sample_config: ExportConfig) -> None:
        sample_config.base_url = "https://example.com/"
        client = _make_client(sample_config)
        assert client.base_api_url == "https://example.com/wp-json/wp/v2"

    def test_bearer_token_header(self, sample_config: ExportConfig) -> None:
        sample_config.token = "my-token"
        client = _make_client(sample_config)
        assert client.session.headers["Authorization"] == "Bearer my-token"

    def test_no_auth_by_default(self, sample_config: ExportConfig) -> None:
        client = _make_client(sample_config)
        assert "Authorization" not in client.session.headers
        assert client.session.auth is None

    def test_basic_auth(self, sample_config: ExportConfig) -> None:
        sample_config.username = "admin"
        sample_config.application_password = "app-pass"
        client = _make_client(sample_config)
        assert client.session.auth == ("admin", "app-pass")

    def test_accept_header_set(self, sample_config: ExportConfig) -> None:
        client = _make_client(sample_config)
        assert client.session.headers["Accept"] == "application/json"

    def test_posts_context_defaults_to_edit(self, sample_config: ExportConfig) -> None:
        client = _make_client(sample_config)
        assert client.posts_context == "edit"


class TestIsAuthError:
    def test_401_is_auth_error(self, sample_config: ExportConfig) -> None:
        resp = MagicMock()
        resp.status_code = 401
        exc = HTTPError(response=resp)
        assert WordPressClient._is_auth_error(exc) is True

    def test_403_is_auth_error(self, sample_config: ExportConfig) -> None:
        resp = MagicMock()
        resp.status_code = 403
        exc = HTTPError(response=resp)
        assert WordPressClient._is_auth_error(exc) is True

    def test_404_not_auth_error(self, sample_config: ExportConfig) -> None:
        resp = MagicMock()
        resp.status_code = 404
        exc = HTTPError(response=resp)
        assert WordPressClient._is_auth_error(exc) is False

    def test_no_response_not_auth_error(self, sample_config: ExportConfig) -> None:
        exc = HTTPError()
        assert WordPressClient._is_auth_error(exc) is False


class TestIsNotFoundError:
    def test_404_is_not_found(self, sample_config: ExportConfig) -> None:
        resp = MagicMock()
        resp.status_code = 404
        exc = HTTPError(response=resp)
        assert WordPressClient._is_not_found_error(exc) is True

    def test_401_not_not_found(self, sample_config: ExportConfig) -> None:
        resp = MagicMock()
        resp.status_code = 401
        exc = HTTPError(response=resp)
        assert WordPressClient._is_not_found_error(exc) is False

    def test_no_response_not_not_found(self, sample_config: ExportConfig) -> None:
        exc = HTTPError()
        assert WordPressClient._is_not_found_error(exc) is False


class TestReport:
    def test_report_calls_reporter(self, sample_config: ExportConfig) -> None:
        reporter = MagicMock()
        client = _make_client(sample_config, progress_reporter=reporter)
        client._report("test message")
        reporter.assert_called_once_with("test message")

    def test_report_does_nothing_without_reporter(
        self, sample_config: ExportConfig
    ) -> None:
        client = _make_client(sample_config, progress_reporter=None)
        client._report("test message")  # should not raise


# ---------------------------------------------------------------------------
# Helper to build paginated response objects
# ---------------------------------------------------------------------------

def _build_response(
    json_data: list,
    total_pages: int = 1,
    status_code: int = 200,
) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.headers = {"X-WP-TotalPages": str(total_pages)}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# get_published_posts
# ---------------------------------------------------------------------------

class TestGetPublishedPosts:
    @patch.object(WordPressClient, "_get_paginated")
    def test_fetches_posts_with_edit_context(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = [{"id": 1}]
        client = _make_client(sample_config)
        client.get_published_posts()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["context"] == "edit"
        assert call_kwargs["params"]["status"] == "publish"

    @patch.object(WordPressClient, "_get_paginated")
    def test_uses_embed_author_and_terms(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = []
        client = _make_client(sample_config)
        client.get_published_posts()
        assert "_embed" in mock_get.call_args[1]["params"]
        assert "author" in mock_get.call_args[1]["params"]["_embed"]
        assert "wp:term" in mock_get.call_args[1]["params"]["_embed"]

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_posts_on_success(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        posts = [{"id": 1}, {"id": 2}]
        mock_get.return_value = posts
        client = _make_client(sample_config)
        result = client.get_published_posts()
        assert result == posts

    @patch.object(WordPressClient, "_get_paginated")
    def test_sets_context_to_edit_on_success(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = []
        client = _make_client(sample_config)
        client.get_published_posts()
        assert client.posts_context == "edit"

    @patch.object(WordPressClient, "_get_paginated")
    def test_falls_back_to_view_on_auth_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        # First call (edit context) raises 401, second (view context) succeeds
        auth_error = HTTPError(response=MagicMock(status_code=401))
        mock_get.side_effect = [auth_error, [{"id": 1}]]
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_published_posts()
        assert result == [{"id": 1}]
        assert client.posts_context == "view"
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_reraises_non_auth_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=500))
        client = _make_client(sample_config)
        with pytest.raises(HTTPError):
            client.get_published_posts()


# ---------------------------------------------------------------------------
# get_categories_map
# ---------------------------------------------------------------------------

class TestGetCategoriesMap:
    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_id_to_name_map(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = [
            {"id": 1, "name": "Tech"},
            {"id": 2, "name": "News"},
        ]
        client = _make_client(sample_config)
        result = client.get_categories_map()
        assert result == {1: "Tech", 2: "News"}

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_empty_map_on_auth_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=401))
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_categories_map()
        assert result == {}
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_empty_map_on_not_found(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=404))
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_categories_map()
        assert result == {}
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_reaises_on_other_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=500))
        client = _make_client(sample_config)
        with pytest.raises(HTTPError):
            client.get_categories_map()

    @patch.object(WordPressClient, "_get_paginated")
    def test_uses_posts_context(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = []
        client = _make_client(sample_config)
        client.posts_context = "view"
        client.get_categories_map()
        assert mock_get.call_args[1]["params"]["context"] == "view"

    @patch.object(WordPressClient, "_get_paginated")
    def test_reports_progress(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.return_value = []
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        client.get_categories_map()
        mock_progress_reporter.assert_any_call("Fetching categories...")


# ---------------------------------------------------------------------------
# get_tags_map
# ---------------------------------------------------------------------------

class TestGetTagsMap:
    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_id_to_name_map(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = [
            {"id": 10, "name": "Python"},
            {"id": 20, "name": "WordPress"},
        ]
        client = _make_client(sample_config)
        result = client.get_tags_map()
        assert result == {10: "Python", 20: "WordPress"}

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_empty_map_on_auth_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=403))
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_tags_map()
        assert result == {}
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_empty_map_on_not_found(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=404))
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_tags_map()
        assert result == {}
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_reaises_on_other_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=500))
        client = _make_client(sample_config)
        with pytest.raises(HTTPError):
            client.get_tags_map()

    @patch.object(WordPressClient, "_get_paginated")
    def test_reports_progress(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.return_value = []
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        client.get_tags_map()
        mock_progress_reporter.assert_any_call("Fetching tags...")


# ---------------------------------------------------------------------------
# get_users_map
# ---------------------------------------------------------------------------

class TestGetUsersMap:
    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_id_to_name_map(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 5, "name": "John Doe"},
        ]
        client = _make_client(sample_config)
        result = client.get_users_map()
        assert result == {1: "Alice", 5: "John Doe"}

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_empty_map_on_auth_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=401))
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_users_map()
        assert result == {}
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_returns_empty_map_on_not_found(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=404))
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client.get_users_map()
        assert result == {}
        assert mock_progress_reporter.called

    @patch.object(WordPressClient, "_get_paginated")
    def test_reaises_on_other_error(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_get.side_effect = HTTPError(response=MagicMock(status_code=500))
        client = _make_client(sample_config)
        with pytest.raises(HTTPError):
            client.get_users_map()

    @patch.object(WordPressClient, "_get_paginated")
    def test_reports_progress(
        self,
        mock_get: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_get.return_value = []
        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        client.get_users_map()
        mock_progress_reporter.assert_any_call("Fetching authors...")


# ---------------------------------------------------------------------------
# _get_paginated
# ---------------------------------------------------------------------------

class TestGetPaginated:
    @patch("wp_exporter.client.requests.Session")
    def test_single_page(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = _build_response([{"id": 1}, {"id": 2}], total_pages=1)

        client = _make_client(sample_config)
        result = client._get_paginated("posts")

        assert len(result) == 2
        assert mock_session.get.call_count == 1

    @patch("wp_exporter.client.requests.Session")
    def test_multiple_pages(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = [
            _build_response([{"id": 1}], total_pages=3),
            _build_response([{"id": 2}], total_pages=3),
            _build_response([{"id": 3}], total_pages=3),
        ]

        client = _make_client(sample_config)
        result = client._get_paginated("posts")

        assert len(result) == 3
        assert mock_session.get.call_count == 3

    @patch("wp_exporter.client.requests.Session")
    def test_passes_params(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = _build_response([])

        client = _make_client(sample_config)
        client._get_paginated("posts", params={"status": "publish"})

        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["params"]["status"] == "publish"
        assert call_kwargs["params"]["per_page"] == 100

    @patch("wp_exporter.client.requests.Session")
    def test_reports_progress(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = _build_response([{"id": 1}], total_pages=1)

        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        client._get_paginated("posts")

        assert mock_progress_reporter.called

    @patch("wp_exporter.client.requests.Session")
    def test_reports_empty_when_no_records(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
        mock_progress_reporter: MagicMock,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = _build_response([])

        client = _make_client(sample_config, progress_reporter=mock_progress_reporter)
        result = client._get_paginated("posts")

        assert result == []
        mock_progress_reporter.assert_any_call("[posts] no records found.")

    @patch("wp_exporter.client.requests.Session")
    def test_raises_on_http_error(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value.raise_for_status.side_effect = HTTPError(
            response=MagicMock(status_code=500)
        )

        client = _make_client(sample_config)
        with pytest.raises(HTTPError):
            client._get_paginated("posts")

    @patch("wp_exporter.client.requests.Session")
    def test_respects_timeout(
        self,
        mock_session_class: MagicMock,
        sample_config: ExportConfig,
    ) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = _build_response([])

        client = _make_client(sample_config)
        client._get_paginated("posts")

        assert mock_session.get.call_args[1]["timeout"] == sample_config.timeout_seconds
