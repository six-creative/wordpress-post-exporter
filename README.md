# WordPress Post Exporter

Python tool to export **all published posts** from a WordPress site using the official REST API (`wp-json/wp/v2`), including post content and taxonomy/author metadata.

## Features

- Exports all published posts with pagination (`per_page=100`).
- Supports `csv` and `sql` output.
- SQL output is MySQL 8 compatible.
- Includes progress logs in the terminal (with optional `--quiet`).
- Tries `context=edit` first, then automatically falls back to `context=view` if unauthorized.
- Preserves the full API payload in `raw_post_json` for custom fields and future migrations.

## Exported Data

Each exported post includes:

- Core fields: `id`, `status`, `type`, `slug`, `link`, `date`, `date_gmt`, `modified`, `modified_gmt`
- Title, excerpt, and content in both flavors when available:
  - `*_rendered`
  - `*_raw` (typically available with `context=edit` + permissions)
- Author:
  - `author_id`
  - `author_name`
- Taxonomies:
  - categories IDs + names
  - tags IDs + names
- Extra fields:
  - `featured_media`, `comment_status`, `ping_status`, `template`, `format`, `meta`
- Full raw JSON payload:
  - `raw_post_json`

## Requirements

- Python 3.10+

## Installation

1. (Optional, recommended) create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Authentication

Use one of the following:

1. Bearer token
- `--token`

2. WordPress Application Password (Basic Auth)
- `--username`
- `--application-password`

Note: public exports also work without credentials in many sites, depending on API exposure rules.

## Usage

### Public/API-view mode (no auth)

```bash
python3 main.py \
  --base-url https://example.com \
  --format csv \
  --output posts.csv
```

### Bearer token

```bash
python3 main.py \
  --base-url https://example.com \
  --token YOUR_TOKEN \
  --format csv \
  --output posts.csv
```

### Username + Application Password

```bash
python3 main.py \
  --base-url https://example.com \
  --username admin \
  --application-password "xxxx xxxx xxxx xxxx" \
  --format sql \
  --output posts.sql
```

## CLI Arguments

- `--base-url` (required): WordPress site base URL. Example: `https://example.com`
- `--format`: `csv` or `sql` (default: `csv`)
- `--output` (required): output file path
- `--token`: bearer token
- `--username`: WordPress username
- `--application-password`: WordPress Application Password
- `--timeout`: timeout in seconds per HTTP request (default: `30`)
- `--quiet`: disable progress logs

## Progress Output

By default, the exporter prints progress messages such as:

```text
[INFO] Starting export...
[INFO] Fetching published posts (context=edit)...
[INFO] No permission for context=edit. Falling back to public mode (context=view).
[INFO] [posts] page 1/12 | accumulated: 100
[INFO] [posts] page 2/12 | accumulated: 200
[INFO] Total posts found: 1200
[INFO] Normalized: 1200/1200
[INFO] Writing CSV file to posts.csv...
Export completed. 1200 posts written to: posts.csv
```

## CSV Format Specification

The CSV header columns are generated in this order:

1. `id`
2. `date`
3. `date_gmt`
4. `modified`
5. `modified_gmt`
6. `slug`
7. `status`
8. `type`
9. `link`
10. `title_rendered`
11. `title_raw`
12. `excerpt_rendered`
13. `excerpt_raw`
14. `content_rendered`
15. `content_raw`
16. `author_id`
17. `author_name`
18. `categories_ids` (JSON array string)
19. `categories_names` (JSON array string)
20. `tags_ids` (JSON array string)
21. `tags_names` (JSON array string)
22. `featured_media`
23. `comment_status`
24. `ping_status`
25. `template`
26. `format`
27. `meta` (JSON object string)
28. `raw_post_json` (full JSON object string)

Notes:
- CSV encoding is UTF-8.
- Content fields may contain long HTML/text.
- JSON-like columns are serialized as JSON strings.

## SQL Format Specification (MySQL 8)

The `.sql` file includes:

1. Session setup:
- `SET NAMES utf8mb4;`
- `SET time_zone = '+00:00';`

2. Schema reset and creation:
- `DROP TABLE IF EXISTS posts;`
- `CREATE TABLE posts (...) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;`

3. Batched inserts:
- `INSERT INTO posts (...) VALUES (...), (...), ...;`

### Column Types

- `id`: `BIGINT NOT NULL` (primary key)
- `author_id`, `featured_media`: `BIGINT NULL`
- `date`, `date_gmt`, `modified`, `modified_gmt`: `DATETIME NULL`
- all remaining columns: `LONGTEXT NULL`

### SQL Compatibility Details

- String escaping is MySQL-safe for:
  - backslash (`\\`)
  - single quote (`\'`)
  - null byte (`\0`)
  - line break (`\n`)
  - carriage return (`\r`)
  - `\x1a` (`\Z`)
- Inserts are chunked (200 rows per statement) to reduce very large single statements.

## Importing SQL into MySQL 8

```bash
mysql -u your_user -p your_database < posts.sql
```

## Project Structure

```text
.
├── main.py
├── requirements.txt
└── wp_exporter
    ├── __init__.py
    ├── client.py
    ├── config.py
    ├── exporters.py
    ├── service.py
    └── transformers.py
```

## Troubleshooting

1. `401` or `403` from API
- Check credentials/permissions.
- Confirm REST API is enabled.
- If `context=edit` is blocked, the exporter automatically retries with `context=view`.

2. Empty `*_raw` fields
- Expected when the authenticated user lacks edit-level permissions.
- In public context, WordPress usually returns only rendered fields.

3. Timeout/network issues
- Increase `--timeout`.
- Check firewall/WAF/proxy restrictions.
