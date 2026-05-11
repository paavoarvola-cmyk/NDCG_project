#!/usr/bin/env python3
"""Fetch Scopus-indexed books that reference:
"Cumulated gain-based evaluation of IR techniques".

Usage:
  export SCOPUS_API_KEY='...'
  python scopus_books_for_cumulated_gain.py --json books.json --csv books.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any

import requests

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
TARGET_REF = "Cumulated gain-based evaluation of IR techniques"


@dataclass
class ScopusBook:
    eid: str
    title: str
    creators: str
    publication_name: str
    cover_date: str
    doi: str
    subtype: str
    citedby_count: str
    scopus_link: str


def build_query(reference_title: str) -> str:
    # DOCTYPE(bk) limits results to books.
    return f'REF("{reference_title}") AND DOCTYPE(bk)'


def _extract_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("search-results", {}).get("entry", [])


def fetch_all_books(api_key: str, query: str, max_results: int = 5000, delay_s: float = 0.2) -> list[dict[str, Any]]:
    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
    }

    all_entries: list[dict[str, Any]] = []
    start = 0
    count = 25  # Scopus API page size commonly capped around 25 for this endpoint.

    unauthorized_view_warned = False

    while True:
        params = {
            "query": query,
            "start": start,
            "count": count,
            "view": "COMPLETE",
        }
        response = requests.get(SCOPUS_SEARCH_URL, headers=headers, params=params, timeout=60)

        # Some API keys do not have access to COMPLETE view.
        if response.status_code == 401 and '"AUTHORIZATION_ERROR"' in response.text and params.get("view") == "COMPLETE":
            params.pop("view", None)
            response = requests.get(SCOPUS_SEARCH_URL, headers=headers, params=params, timeout=60)
            if not unauthorized_view_warned:
                print(
                    "Warning: API key is not authorized for view=COMPLETE; falling back to default view.",
                    file=sys.stderr,
                )
                unauthorized_view_warned = True

        if response.status_code != 200:
            raise RuntimeError(
                f"Scopus API request failed: HTTP {response.status_code}\n{response.text[:1000]}"
            )

        payload = response.json()
        entries = _extract_entries(payload)
        search_results = payload.get("search-results", {})
        entries = search_results.get("entry", [])

        if not entries:
            break

        all_entries.extend(entries)

        if len(all_entries) >= max_results:
            break

        # If fewer than requested are returned, we reached last page.
        if len(entries) < count:
            break

        start += count
        time.sleep(delay_s)

    return all_entries[:max_results]


def normalize_entry(entry: dict[str, Any]) -> ScopusBook:
    links = entry.get("link", [])
    scopus_link = ""
    for link in links:
        if link.get("@ref") == "scopus":
            scopus_link = link.get("@href", "")
            break

    return ScopusBook(
        eid=entry.get("eid", ""),
        title=entry.get("dc:title", ""),
        creators=entry.get("dc:creator", ""),
        publication_name=entry.get("prism:publicationName", ""),
        cover_date=entry.get("prism:coverDate", ""),
        doi=entry.get("prism:doi", ""),
        subtype=entry.get("subtypeDescription", ""),
        citedby_count=entry.get("citedby-count", ""),
        scopus_link=scopus_link,
    )


def write_csv(books: list[ScopusBook], output_path: str) -> None:
    fieldnames = list(asdict(books[0]).keys()) if books else [
        "eid",
        "title",
        "creators",
        "publication_name",
        "cover_date",
        "doi",
        "subtype",
        "citedby_count",
        "scopus_link",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for book in books:
            writer.writerow(asdict(book))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.getenv("SCOPUS_API_KEY"), help="Scopus API key (or set SCOPUS_API_KEY).")
    parser.add_argument("--reference-title", default=TARGET_REF, help="Referenced work title to search for.")
    parser.add_argument("--json", default="scopus_books.json", help="JSON output path.")
    parser.add_argument("--csv", default="scopus_books.csv", help="CSV output path.")
    parser.add_argument("--max-results", type=int, default=5000, help="Maximum number of records to fetch.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Error: missing Scopus API key. Use --api-key or SCOPUS_API_KEY.", file=sys.stderr)
        return 2

    query = build_query(args.reference_title)
    print(f"Query: {query}")

    entries = fetch_all_books(api_key=args.api_key, query=query, max_results=args.max_results)
    books = [normalize_entry(e) for e in entries]

    with open(args.json, "w", encoding="utf-8") as jf:
        json.dump([asdict(b) for b in books], jf, indent=2, ensure_ascii=False)

    write_csv(books, args.csv)

    print(f"Fetched {len(books)} book records.")
    print(f"Saved JSON: {args.json}")
    print(f"Saved CSV:  {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
