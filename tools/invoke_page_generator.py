#!/usr/bin/env python3
"""Invoke the page generator Lambda and fail clearly if publishing fails."""

from __future__ import annotations

import argparse
import json
from typing import Any

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Invoke the page generator Lambda to republish the static site."
    )
    parser.add_argument(
        "--function-name",
        required=True,
        help="Lambda function name to invoke",
    )
    parser.add_argument(
        "--region",
        default="us-east-2",
        help="AWS region for the Lambda client (default: us-east-2)",
    )
    return parser.parse_args()


def invoke_page_generator(function_name: str, region: str) -> dict[str, Any]:
    client = boto3.client("lambda", region_name=region)
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"source": "terraform-apply"}).encode("utf-8"),
    )

    payload_bytes = response["Payload"].read()
    payload_text = payload_bytes.decode("utf-8") if payload_bytes else ""

    if response.get("FunctionError"):
        raise RuntimeError(
            f"Page generator Lambda returned FunctionError={response['FunctionError']}: {payload_text}"
        )

    if not payload_text:
        raise RuntimeError("Page generator Lambda returned an empty payload")

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Page generator Lambda returned invalid JSON: {payload_text}") from exc

    status_code = payload.get("statusCode")
    if status_code != 200:
        raise RuntimeError(f"Page generator Lambda returned statusCode={status_code}: {payload_text}")

    return payload


def main() -> int:
    args = parse_args()
    payload = invoke_page_generator(function_name=args.function_name, region=args.region)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
