import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}


def load_cookies(auth_file: str) -> RequestsCookieJar:
    """Load cookies from a Playwright storageState JSON file into a RequestsCookieJar."""
    with open(auth_file) as f:
        data = json.load(f)

    jar = RequestsCookieJar()
    for cookie in data.get("cookies", []):
        jar.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )
    return jar


def fetch_html(
    url: str, timeout: int = 10, cookies: RequestsCookieJar | None = None
) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout, cookies=cookies)
    response.raise_for_status()
    return response.text


def parse_metatags(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    result = {
        "title": None,
        "charset": None,
        "name": {},
        "property": {},
        "http_equiv": {},
    }

    title_tag = soup.find("title")
    if title_tag:
        result["title"] = title_tag.get_text(strip=True)

    for tag in soup.find_all("meta"):
        attrs = tag.attrs

        if "charset" in attrs:
            result["charset"] = attrs["charset"]
        elif "name" in attrs:
            key = str(attrs["name"]).lower()
            result["name"][key] = attrs.get("content", "")
        elif "property" in attrs:
            key = str(attrs["property"]).lower()
            result["property"][key] = attrs.get("content", "")
        elif "http-equiv" in attrs:
            key = str(attrs["http-equiv"]).lower()
            result["http_equiv"][key] = attrs.get("content", "")
        # silently skip tags with none of those attributes

    return result


def scrape(url: str, timeout: int = 10, auth_file: str | None = None) -> dict:
    cookies = load_cookies(auth_file) if auth_file else None
    html = fetch_html(url, timeout=timeout, cookies=cookies)
    return parse_metatags(html)


def scrape_many(
    urls: list[str],
    timeout: int = 10,
    auth_file: str | None = None,
    max_workers: int = 1,
) -> list[dict]:
    """
    Scrape metatags for a list of URLs concurrently and return all results as a list.

    Uses a ThreadPoolExecutor with up to max_workers threads. Defaults to 1
    (sequential execution) to avoid unintentionally hitting rate limits on the
    target server. Increase max_workers to enable concurrent scraping. Results
    are returned in the same order as the input URLs regardless of completion
    order — each future is mapped back to its original index via a pre-allocated
    results list.

    Each entry has "url" as its first key so results are self-identifying.
    Failed URLs are recorded as {"url": ..., "error": "..."} rather than
    raising, so one bad URL never aborts the rest of the batch.
    """
    logger = logging.getLogger(__name__)
    total = len(urls)
    results: list[dict | None] = [None] * total

    with logging_redirect_tqdm():
        with tqdm(total=total, desc="Scraping", unit="URL", colour="green") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(scrape, url, timeout, auth_file): i
                    for i, url in enumerate(urls)
                }
                for future in as_completed(futures):
                    i = futures[future]
                    url = urls[i]
                    try:
                        results[i] = {"url": url, **future.result()}
                        logger.debug("%d/%d Scraped: '%s'.", i + 1, total, url)
                    except Exception as exc:
                        logger.warning("Failed to scrape '%s': %s", url, exc)
                        results[i] = {"url": url, "error": str(exc)}
                    pbar.update(1)

    return results  # type: ignore[return-value]
