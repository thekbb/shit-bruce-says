#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lambda"))

import page_generator  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch DynamoDB Local and republish the local static site when quotes change."
    )
    parser.add_argument("--api", required=True, help="Local API base URL, e.g. http://127.0.0.1:3000")
    parser.add_argument(
        "--site-url",
        default="http://localhost:8080",
        help="Base URL for the local static site (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--table-name",
        default="bruce-quotes",
        help="DynamoDB table name (default: bruce-quotes)",
    )
    parser.add_argument(
        "--ddb-endpoint",
        default="http://localhost:8000",
        help="DynamoDB Local endpoint (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--output-dir",
        default="web",
        help="Directory to write generated static files into (default: web)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: 2.0)",
    )
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> None:
    os.environ["AWS_REGION"] = "us-east-2"
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["TABLE_NAME"] = args.table_name
    os.environ["DYNAMODB_ENDPOINT"] = args.ddb_endpoint
    os.environ["API_BASE_URL"] = args.api.rstrip("/")
    os.environ["SITE_BASE_URL"] = args.site_url.rstrip("/")
    os.environ["DOMAIN"] = args.site_url.removeprefix("https://").removeprefix("http://").rstrip("/")
    os.environ["LOCAL_SITE_DIR"] = args.output_dir
    page_generator._dynamodb_resource = None
    page_generator._s3_client = None


def quote_fingerprint(quotes: list[dict[str, Any]]) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (
            str(quote.get("SK", "")),
            str(quote.get("createdAt", "")),
            str(quote.get("quote", "")),
        )
        for quote in quotes
    )


def main() -> int:
    args = parse_args()
    configure_environment(args)

    last_fingerprint: tuple[tuple[str, str, str], ...] | None = None
    print(f"Watching {args.table_name} at {args.ddb_endpoint} and publishing into {args.output_dir}")

    try:
        while True:
            quotes = page_generator.fetch_all_quotes()
            current_fingerprint = quote_fingerprint(quotes)
            if current_fingerprint != last_fingerprint:
                result = page_generator.publish_site()
                last_fingerprint = current_fingerprint
                print(f"Published local static site ({result['quoteCount']} quotes)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped local site watcher")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
