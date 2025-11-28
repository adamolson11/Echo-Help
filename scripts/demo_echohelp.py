"""Simple CLI demo that calls the EchoHelp HTTP API and pretty-prints search results.

Usage:
  PYTHONPATH=. python -m scripts.demo_echohelp
  ECHOHELP_API_BASE can be set to point to a different host (default: http://localhost:8000)
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List
import argparse

import requests
from requests.exceptions import RequestException


DEFAULT_BASE_URL = "http://localhost:8000"
API_BASE = os.getenv("ECHOHELP_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def pretty_print_result(result: Dict[str, Any], index: int) -> None:
    ticket_id = result.get("id") or result.get("ticket_id") or "unknown-id"
    title = result.get("title") or result.get("summary") or "(no title)"
    snippet = (
        result.get("snippet")
        or result.get("summary")
        or result.get("description")
        or ""
    )
    snippet = snippet.strip().replace("\n", " ")
    if len(snippet) > 200:
        snippet = snippet[:197] + "..."

    print(f"{index}. [{ticket_id}] {title}")
    if snippet:
        print(f"   {snippet}")
    # Show source if present
    src = result.get("source")
    ext = result.get("external_key")
    meta = []
    if src:
        meta.append(str(src).upper())
    if ext:
        meta.append(str(ext))
    if meta:
        print(f"   ({', '.join(meta)})")
    print()


def run_search_demo(queries: List[str], limit: int = 5, json_mode: bool = False) -> int:
    url = f"{API_BASE}/api/search"
    print(f"Using API base: {API_BASE}")
    print(f"POST {url}")
    print()

    session = requests.Session()

    for query in queries:
        payload = {"q": query, "limit": limit}

        print("=" * 80)
        print(f"Query: {query}")
        print("-" * 80)

        try:
            start = time.time()
            resp = session.post(url, json=payload, timeout=10)
            elapsed = time.time() - start
        except RequestException as exc:
            print(f"ERROR: Could not connect to {url}")
            print(f"Detail: {exc}")
            print("Make sure the backend is running and reachable.")
            print()
            return 1

        if not resp.ok:
            print(f"ERROR: Server returned HTTP {resp.status_code}")
            try:
                print("Response body:", resp.text)
            except Exception:
                pass
            print()
            return 1

        try:
            data = resp.json()
        except ValueError:
            print("ERROR: Response was not valid JSON.")
            print("Raw body:", resp.text[:500])
            print()
            return 1

        if json_mode:
            print("Raw JSON response:")
            print(data)
            print()

        # Support different response shapes
        results = []
        if isinstance(data, dict):
            results = data.get("results") or data.get("tickets") or []
        elif isinstance(data, list):
            results = data

        print(f"Received {len(results)} result(s) in {elapsed:.2f}s")
        print()

        if not results:
            print("No results found.")
            print()
            continue

        for idx, result in enumerate(results[:limit], start=1):
            pretty_print_result(result, index=idx)

    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="EchoHelp demo CLI")
    parser.add_argument(
        "--mode",
        choices=["search", "ingest-search"],
        default="search",
        help="Demo mode to run.",
    )
    parser.add_argument("queries", nargs="*", help="Optional queries for search mode.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print raw JSON responses for debugging.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=1.0,
        help="Seconds to wait after ingest before searching (ingest-search mode only).",
    )

    args = parser.parse_args(argv[1:])

    if args.mode == "ingest-search":
        return run_ingest_and_search_demo(wait_seconds=args.wait_seconds, json_mode=args.json)

    if args.queries:
        queries = args.queries
    else:
        queries = [
            "vpn not connecting for remote user",
            "password reset issue",
            "printer not working",
        ]

    return run_search_demo(queries, json_mode=args.json)


def run_ingest_and_search_demo(wait_seconds: float = 1.0, json_mode: bool = False) -> int:
    """Demonstrate end-to-end ingest -> search.

    Posts a synthetic thread to `/api/ingest/thread`, then searches for a
    keyword from that thread to validate the ingest → embedding → search flow.
    """
    ingest_url = f"{API_BASE}/api/ingest/thread"
    search_url = f"{API_BASE}/api/search"

    session = requests.Session()

    # Synthetic thread — kept small and likely to match simple queries
    thread = {
        "source": "demo",
        "external_id": "DEMO-INGEST-001",
        "title": "VPN disconnects for remote user",
        "resolved": True,
        "resolution_notes": "Updated VPN client and restarted service",
        "messages": [
            {"author": "user", "text": "VPN disconnects every 20 minutes with AUTH_FAILED."},
            {"author": "agent", "text": "We updated your client and reset profile; seems resolved."},
        ],
    }

    print(f"Using API base: {API_BASE}")
    print(f"POST {ingest_url}")
    print()

    try:
        resp = session.post(ingest_url, json=thread, timeout=10)
    except RequestException as exc:
        print(f"ERROR: Could not connect to {ingest_url}")
        print(f"Detail: {exc}")
        print("Make sure the backend is running and the ingest endpoint exists.")
        print()
        return 1

    if not resp.ok:
        print(f"ERROR: Ingest endpoint returned HTTP {resp.status_code}")
        try:
            print("Response body:", resp.text)
        except Exception:
            pass
        print()
        return 1

    try:
        ingest_data = resp.json()
    except ValueError:
        ingest_data = {"raw_body": resp.text[:500]}

    print("Ingest response:")
    print(ingest_data)
    print()

    # Pause to let embedding complete (configurable)
    time.sleep(float(wait_seconds))

    query = "vpn auth_failed"
    payload = {"q": query, "limit": 5}

    print("=" * 80)
    print(f"Now searching for: {query}")
    print("-" * 80)

    try:
        start = time.time()
        search_resp = session.post(search_url, json=payload, timeout=10)
        elapsed = time.time() - start
    except RequestException as exc:
        print(f"ERROR: Could not connect to {search_url}")
        print(f"Detail: {exc}")
        print()
        return 1

    if not search_resp.ok:
        print(f"ERROR: Search endpoint returned HTTP {search_resp.status_code}")
        try:
            print("Response body:", search_resp.text)
        except Exception:
            pass
        print()
        return 1

    try:
        data = search_resp.json()
    except ValueError:
        print("ERROR: Search response was not valid JSON.")
        print("Raw body:", search_resp.text[:500])
        print()
        return 1

    results = []
    if isinstance(data, dict):
        results = data.get("results") or data.get("tickets") or []
    elif isinstance(data, list):
        results = data

    print(f"Received {len(results)} result(s) in {elapsed:.2f}s")
    print()

    if json_mode:
        print("Raw JSON response:")
        print(data)
        print()

    if not results:
        print("No results found. Check that ingest attaches content to the index/search pipeline.")
        print()
        return 0

    for idx, result in enumerate(results[:5], start=1):
        pretty_print_result(result, index=idx)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
