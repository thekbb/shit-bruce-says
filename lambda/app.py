import os
import json
import re
import time
import base64
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

MAX_INPUT_LENGTH = 300
MIN_INPUT_LENGTH = 5

SQLISH = re.compile(
    r"""
    (?:--|;|/\*|\*/|\#)                    # SQL comments / separators (note the escaped \#)
    | \b(?:SELECT|INSERT|UPDATE|DELETE)\b  # DML verbs in ALL CAPS
      .*? \bFROM\b                         # ...followed somewhere by FROM (ALL CAPS)
    | \bUNION\s+SELECT\b                   # UNION SELECT in ALL CAPS
    | \b(?:DROP|EXEC|EXECUTE|SLEEP|WAITFOR|XP_)\b  # dangerous verbs (ALL CAPS)
    | \bOR\s+1\s*=\s*1\b                   # classic tautology (ALL CAPS)
    """,
    re.X,
)

REGION = os.getenv("AWS_REGION", "us-east-2")
TABLE_NAME = os.getenv("TABLE_NAME", "bruce-quotes")

def _route(event):
    http = event.get("requestContext", {}).get("http", {})
    method = (http.get("method") or event.get("httpMethod") or "GET").upper()

    # Prefer rawPath (HTTP API v2), fall back to requestContext.http.path, then legacy 'path'
    path = event.get("rawPath") or http.get("path") or event.get("path") or "/"

    # normalize: collapse multiple slashes and strip trailing slash (except root)
    path = re.sub(r'//+', '/', path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    if method == "GET" and path == "/quotes":
        return _get_quotes(event, None)
    if method == "POST" and path == "/quotes":
        return _post_quote(event, None)

    return _resp(404, {"error": "Not found"})

# lazy table getter so moto can patch boto3 before first use
_table = None
def _get_table():
    global _table
    if _table is None:
        endpoint_url = os.getenv("DYNAMODB_ENDPOINT")  # e.g., http://localhost:8000
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.getenv("AWS_REGION", "us-east-2"),
            endpoint_url=endpoint_url,
        )
        _table = dynamodb.Table(os.getenv("TABLE_NAME", "bruce-quotes"))
    return _table

def _resp(code: int, obj: dict, headers: dict | None = None):
    h = {"content-type": "application/json", "cache-control": "no-store"}
    if headers:
        h.update(headers)
    return {"statusCode": code, "headers": h, "body": json.dumps(obj)}

def _ulid() -> str:
    ms = int(time.time() * 1000).to_bytes(6, "big")
    rnd = os.urandom(10)
    return base64.b32encode(ms + rnd).decode().rstrip("=").upper()

def _get_quotes(event, _ctx):
    qs = event.get("queryStringParameters") or {}
    try:
        limit = int(qs.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))

    eks = None
    if qs.get("cursor"):
        try:
            eks = json.loads(qs["cursor"])
        except Exception:
            eks = None

    kwargs = {
        "KeyConditionExpression": Key("PK").eq("QUOTE"),
        "ScanIndexForward": False,
        "Limit": limit,
    }
    if eks is not None:
        kwargs["ExclusiveStartKey"] = eks

    res = _get_table().query(**kwargs)
    return _resp(
        200,
        {"items": res.get("Items", []), "cursor": res.get("LastEvaluatedKey")},
        headers={"access-control-allow-origin": "*"},
    )

def _post_quote(event, _ctx):
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return _resp(400, {"error": "Invalid JSON"})

    quote = (body.get("quote") or "").strip()
    n = len(quote)
    if not (MIN_INPUT_LENGTH <= n <= MAX_INPUT_LENGTH):
        return _resp(400, {"error": f"Quote length must be between {MIN_INPUT_LENGTH} and {MAX_INPUT_LENGTH}."})
    if SQLISH.search(quote):
        return _resp(400, {"error": "Input contains SQL-like content. There is no SQL here."})

    now = datetime.now(timezone.utc).isoformat()
    item = {"PK": "QUOTE", "SK": _ulid(), "quote": quote, "createdAt": now}
    _get_table().put_item(Item=item)
    return _resp(201, {"createdAt": now}, headers={"access-control-allow-origin": "*"})

def handler(event, ctx):
    http = (event.get("requestContext", {}).get("http") or {})
    method = http.get("method", "GET")
    path = http.get("path", "/")

    if method == "GET" and path == "/quotes":
        return _get_quotes(event, ctx)
    if method == "POST" and path == "/quotes":
        return _post_quote(event, ctx)

    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET,POST,OPTIONS",
                "access-control-allow-headers": "content-type",
            },
            "body": "",
        }

    return _resp(404, {"error": "Not found"})
