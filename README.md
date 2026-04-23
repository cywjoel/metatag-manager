# metatag-manager

A command-line tool for scraping HTML meta tags from one or more URLs. Supports bulk input from multiple file formats, session cookie authentication, concurrent scraping, and structured JSON output.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Single URL](#single-url)
  - [Multiple URLs](#multiple-urls)
  - [Reading URLs from a File](#reading-urls-from-a-file)
- [URL Input File Formats](#url-input-file-formats)
  - [Plain Text (.txt)](#plain-text-txt)
  - [JSON (.json)](#json-json)
  - [Excel (.xlsx)](#excel-xlsx)
  - [CSV (.csv)](#csv-csv)
- [Output](#output)
  - [Pretty-print (default)](#pretty-print-default)
  - [JSON](#json-output)
  - [Writing to a File](#writing-to-a-file)
- [Authentication](#authentication)
  - [Using an Existing Auth File](#using-an-existing-auth-file)
  - [Generating an Auth File with Playwright](#generating-an-auth-file-with-playwright)

- [Concurrency](#concurrency)
- [Logging](#logging)
- [CLI Reference](#cli-reference)
- [Dependencies](#dependencies)

---

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

---

## Installation

```sh
# Install Python dependencies
uv sync

# Install Playwright's Chromium browser (only needed for utils/create_login.py)
uv run playwright install chromium
```

---

## Project Structure

```
metatag-manager/
├── main.py                        # CLI entry point
├── scraper.py                     # Core scraping logic
├── pyproject.toml
├── auth.json                      # Session cookies (generated — do not commit)
└── utils/
    ├── connectors.py              # URL input connectors (.txt, .json, .xlsx, .csv)
    └── create_login.py            # Generate auth.json using Playwright
```

---

## Quick Start

```sh
# Scrape a single URL and print results
uv run main.py https://example.com

# Scrape a list of URLs from an Excel file and save results to JSON
uv run main.py --file urls.xlsx --sheet "Pages" --output results.json
```

---

## Usage

### Single URL

With no flags, a single URL is printed in a human-readable format:

```sh
uv run main.py https://example.com
```

```
Title:   Example Domain
Charset: UTF-8

[NAME]
  viewport: width=device-width, initial-scale=1
  description: An example page

[PROPERTY]
  og:title: Example Domain
  og:image: https://example.com/image.png

[HTTP-EQUIV]
  content-type: text/html; charset=utf-8
```

### Multiple URLs

Pass URLs as positional arguments, via `--file`, or combine both. Multiple URLs always produce JSON output.

```sh
# Inline
uv run main.py https://example.com https://example.com/about

# From a file
uv run main.py --file urls.txt

# Both combined
uv run main.py https://example.com --file more-urls.txt
```

### Reading URLs from a File

The `--file` flag accepts four formats, detected automatically by file extension:

```sh
uv run main.py --file urls.txt
uv run main.py --file urls.json
uv run main.py --file urls.xlsx --sheet "Page List"
uv run main.py --file urls.xlsx --sheet "Page List" --url-column "Page URL"
uv run main.py --file urls.csv
```

---

## URL Input File Formats

### Plain Text (.txt)

One URL per line. Blank lines and lines beginning with `#` are ignored.

```
# Production pages
https://example.com
https://example.com/about

https://example.com/contact
```

### JSON (.json)

A top-level JSON array. Each item may be a plain string or an object containing a `url` key (case-insensitive). All other keys are ignored.

```json
[
  { "name": "Home",    "url": "https://example.com" },
  { "name": "About",   "url": "https://example.com/about" },
  { "name": "Contact", "url": "https://example.com/contact" }
]
```

### Excel (.xlsx)

By default, the connector looks for a column with the header `URL` (case-insensitive). Use `--url-column` to specify a different column header if your sheet uses a different name. All other columns are ignored. Use `--sheet` to specify a sheet by name; the workbook's active sheet is used by default.

| Name    | URL                           | Description        |
|---------|-------------------------------|--------------------|
| Home    | https://example.com           | Homepage           |
| About   | https://example.com/about     | About page         |
| Contact | https://example.com/contact   | Contact page       |

```sh
# Default — looks for a column named "URL"
uv run main.py --file urls.xlsx --sheet "Page List" --output results.json

# Custom column name
uv run main.py --file urls.xlsx --sheet "Page List" --url-column "Page URL" --output results.json
```

### CSV (.csv)

Every non-empty cell across all rows is treated as a URL. Multiple URLs may appear on one row or across multiple rows.

```
https://example.com,https://example.com/about
https://example.com/contact
```

---

## Output

### Pretty-print (default)

Used automatically for a single URL with no `--json` or `--output` flag. Grouped by meta tag type.

### JSON Output

Always used when scraping multiple URLs. Can also be requested explicitly for a single URL with `--json`. The result includes `url` as the first key in each entry.

```json
[
  {
    "url": "https://example.com",
    "title": "Example Domain",
    "charset": "UTF-8",
    "name": {
      "viewport": "width=device-width, initial-scale=1",
      "description": "An example page"
    },
    "property": {
      "og:title": "Example Domain"
    },
    "http_equiv": {}
  },
  {
    "url": "https://broken.example.com",
    "error": "404 Client Error: Not Found"
  }
]
```

Failed URLs are recorded inline as `{ "url": "...", "error": "..." }` rather than aborting the entire run.

### Writing to a File

Use `--output` to write JSON to a file instead of stdout. This implies `--json`.

```sh
uv run main.py --file urls.xlsx --output results.json
```

---

## Authentication

Some sites require session cookies to access. The `--auth` flag accepts a Playwright `storageState` JSON file and forwards its cookies with every request.

### Using an Existing Auth File

```sh
uv run main.py --file urls.xlsx --auth auth.json --output results.json
```

### Generating an Auth File with Playwright

**Note: this is a highly specific function that uses Playwright to load a website with a password-protected Vercel domain and enter the password on the page. If you are scraping a domain that does not have such a protection; feel free to ignore it; if you are scraping a domain with other types of protections, you should provide your own `auth.json` or similar file.*

Use this for Vercel password-protected deployments.

```sh
# Prompts for password securely (recommended)
uv run utils/create_login.py https://example.com

# Pass password explicitly (e.g. in a CI environment)
uv run utils/create_login.py https://example.com --password "secret"

# Custom output path
uv run utils/create_login.py https://example.com --output my-auth.json
```

| Argument | Default | Description |
|---|---|---|
| `login_url` | — | URL of the password-protected site (positional, required) |
| `--password` | — | Site password. If omitted, you will be prompted to enter it securely |
| `--output FILE` | `auth.json` | Destination file for the exported session cookies |

---

## Concurrency

By default the scraper runs sequentially (`--workers 1`) to avoid unintentionally hitting rate limits. Increase `--workers` to enable concurrent scraping:

```sh
# Sequential (default — safe for unknown servers)
uv run main.py --file urls.xlsx --output results.json

# 5 concurrent workers (moderate)
uv run main.py --file urls.xlsx --output results.json --workers 5

# 20 concurrent workers (aggressive — only use if you control the server
# or know it can handle the load)
uv run main.py --file urls.xlsx --output results.json --workers 20
```

Results are always written in the same order as the input URLs, regardless of which requests finish first.

---

## Logging

Log output is written to the console at `INFO` level by default.

```sh
# Default INFO logging
uv run main.py --file urls.xlsx --output results.json

# Verbose DEBUG logging (includes per-URL detail, column indices, raw HTTP logs)
uv run main.py --file urls.xlsx --output results.json -v

# Write logs to a file (appends; directory is created automatically)
uv run main.py --file urls.xlsx --output results.json --log-file logs/run.log

# All options combined
uv run main.py --file urls.xlsx --output results.json -v --log-file logs/run.log
```

The console and file use slightly different formats:

| Destination | Format |
|-------------|--------|
| Console     | `HH:MM:SS [LEVEL] message` |
| File        | `HH:MM:SS [LEVEL] module: message` |

The file format includes the source module name (e.g. `utils.connectors`, `scraper`) for easier post-run tracing.

> **Note:** Enabling `-v` also activates `DEBUG` logging from `urllib3` (the HTTP library used by `requests`), which logs every raw HTTP request and response in the format `host:port "METHOD path HTTP/version" status_code content_length`. A `content_length` of `None` means the server used chunked transfer encoding and did not declare a `Content-Length` header.

---

## CLI Reference

```
usage: main.py [-h] [--file FILE] [--json] [--sheet SHEET] [--url-column COLUMN]
               [--output FILE] [--timeout TIMEOUT] [--auth FILE] [-v]
               [--workers N] [--log-file FILE]
               [url ...]
```

| Argument | Default | Description |
|---|---|---|
| `url` | — | One or more URLs to scrape (positional, optional if `--file` is used) |
| `--file FILE` | — | Path to a `.txt`, `.json`, `.xlsx`, or `.csv` file containing URLs |
| `--sheet SHEET` | Active sheet | Sheet name to read from (`.xlsx` files only) |
| `--url-column COLUMN` | `URL` | Column header to read URLs from (`.xlsx` files only, case-insensitive) |
| `--json` | Off | Force JSON output for a single URL |
| `--output FILE` | stdout | Write JSON output to a file (implies `--json`) |
| `--timeout N` | `10` | HTTP request timeout in seconds |
| `--auth FILE` | — | Playwright `storageState` JSON file for cookie-based authentication |
| `--workers N` | `1` | Number of concurrent scraping workers (1 = sequential) |
| `-v`, `--verbose` | Off | Enable DEBUG-level logging |
| `--log-file FILE` | — | Write log output to a file in addition to the console |

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP fetching |
| `beautifulsoup4` | HTML parsing |
| `lxml` | Fast HTML parser backend for BeautifulSoup |
| `openpyxl` | Reading `.xlsx` Excel files |
| `tqdm` | Progress bars |
| `playwright` | Browser automation for JavaScript-rendered login flows |
