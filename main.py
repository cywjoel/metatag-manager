import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from src.scraper import scrape, scrape_many
from src.utils.connectors import read_file


def _pretty_print(result: dict) -> None:
    print(f"Title:   {result['title']}")
    print(f"Charset: {result['charset']}")

    sections = [
        ("name", "NAME"),
        ("property", "PROPERTY"),
        ("http_equiv", "HTTP-EQUIV"),
    ]

    for key, label in sections:
        bucket = result.get(key, {})
        if not bucket:
            continue
        print(f"\n[{label}]")
        for k, v in bucket.items():
            print(f"  {k}: {v}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch and display meta tags for one or more URLs. "
            "URLs can be supplied as positional arguments, via --file, or both."
        )
    )
    parser.add_argument(
        "url",
        nargs="*",
        help="One or more URLs to scrape.",
    )
    parser.add_argument(
        "--file",
        default=None,
        metavar="FILE",
        help=(
            "Path to a file containing URLs to scrape. "
            "Supported formats: .txt (one URL per line), "
            ".json (array of objects with a 'url' key), "
            ".xlsx (rows with a 'URL' column header), "
            ".csv (comma-separated URLs). "
            "Use --sheet to specify a sheet name for .xlsx files."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (always used when more than one URL is scraped).",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        metavar="SHEET",
        help="Sheet name to read from when --file points to an .xlsx file. Defaults to the active sheet.",
    )
    parser.add_argument(
        "--url-column",
        default="URL",
        metavar="COLUMN",
        help="Column header name to read URLs from in .xlsx files (default: 'URL', case-insensitive).",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write JSON output to a file instead of stdout (implies --json).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP request timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--auth",
        default=None,
        metavar="FILE",
        help="Path to a Playwright storageState JSON file whose cookies will be forwarded with every request.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug-level logging for detailed progress output.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help="Number of concurrent workers for scraping multiple URLs (default: 1, i.e. sequential). Increase to scrape faster, but be mindful of rate limits on the target server.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="FILE",
        help="Write log output to a file in addition to the console (appends if the file already exists).",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    log_datefmt = "%H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=log_datefmt,
    )

    if args.log_file:
        try:
            Path(args.log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(args.log_file, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt=log_datefmt,
                )
            )
            logging.getLogger().addHandler(file_handler)
        except OSError as e:
            print(f"Error opening log file: {e}", file=sys.stderr)
            sys.exit(1)

    # --- Collect URLs from positional args and/or --file ---
    urls: list[str] = list(args.url)

    if args.file:
        try:
            file_urls = read_file(
                args.file, sheet_name=args.sheet, url_column=args.url_column
            )
            urls.extend(file_urls)
        except (OSError, ValueError) as e:
            print(f"Error reading --file: {e}", file=sys.stderr)
            sys.exit(1)

    if not urls:
        parser.error("Provide at least one URL as a positional argument or via --file.")

    # --- Scrape & Output ---
    shared: dict[str, Any] = {
        "timeout": args.timeout,
        "auth_file": args.auth,
        "max_workers": args.workers,
    }
    multi = len(urls) > 1
    as_json = multi or args.json or args.output

    if not as_json:
        # Single URL, pretty-print — exit early so no JSON path is needed
        try:
            result = scrape(urls[0], **shared)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        _pretty_print(result)
        return

    # JSON path — build payload first, then decide where to send it
    if multi:
        payload = json.dumps(scrape_many(urls, **shared), indent=2)
    else:
        try:
            payload = json.dumps(scrape(urls[0], **shared), indent=2)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(payload)
            print(f"Saved to '{args.output}'.")
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(payload)


if __name__ == "__main__":
    main()
