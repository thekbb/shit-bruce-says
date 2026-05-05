import os
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import boto3

class Config:
    """Application configuration constants."""
    MAX_INPUT_LENGTH = 300
    MIN_INPUT_LENGTH = 5
    REGION = os.getenv("AWS_REGION", "us-east-2")
    TABLE_NAME = os.getenv("TABLE_NAME", "bruce-quotes")


def get_cors_origin() -> str:
    """
    Get the CORS origin configuration.

    Returns '*' for local development, or the Terraform-configured value for production.
    This allows the API to accept requests from the configured frontend domain.

    Returns:
        str: CORS origin value ('*' for dev, specific domain for prod)
    """
    return os.getenv("ALLOW_ORIGIN", "*")  # '*' for local, Terraform sets this in prod

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

def _route(event: dict[str, Any], ctx: Optional[Any] = None) -> dict[str, Any]:
    """
    Route incoming API Gateway events to appropriate handlers.

    Handles both HTTP API v2 and REST API event formats, normalizes paths,
    and routes to GET/POST/OPTIONS handlers. Returns 404 for unknown routes.

    Args:
        event: API Gateway event payload containing request details
        ctx: Lambda context object (unused but kept for consistency)

    Returns:
        dict: API Gateway response with statusCode, headers, and body
    """
    http = event.get("requestContext", {}).get("http", {})
    method = (http.get("method") or event.get("httpMethod") or "GET").upper()

    # Prefer rawPath (HTTP API v2), fall back to requestContext.http.path, then legacy 'path'
    path = event.get("rawPath") or http.get("path") or event.get("path") or "/"

    # normalize: collapse multiple slashes and strip trailing slash (except root)
    path = re.sub(r'//+', '/', path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    if method == "POST" and path == "/quotes":
        return _post_quote(event, ctx)
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "access-control-allow-origin": get_cors_origin(),
                "access-control-allow-methods": "GET,POST,OPTIONS",
                "access-control-allow-headers": "content-type",
            },
            "body": "",
        }

    return _resp(404, {"error": "Not found"})

# lazy table getter so moto can patch boto3 before first use
_table: Optional[Any] = None
_lambda_client: Optional[Any] = None

def _get_table() -> Any:
    """
    Get the DynamoDB table resource using lazy initialization.

    Creates and caches a boto3 DynamoDB Table resource on first call.
    Supports local DynamoDB endpoint for testing via DYNAMODB_ENDPOINT env var.
    Uses global singleton pattern to avoid creating new resources per invocation.

    Returns:
        Table: boto3 DynamoDB Table resource for the quotes table

    Environment Variables:
        DYNAMODB_ENDPOINT: Optional local endpoint (e.g., http://localhost:8000)
        TABLE_NAME: DynamoDB table name (default: "bruce-quotes")
    """
    global _table
    if _table is None:
        endpoint_url = os.getenv("DYNAMODB_ENDPOINT")  # e.g., http://localhost:8000
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=Config.REGION,
            endpoint_url=endpoint_url,
        )
        _table = dynamodb.Table(Config.TABLE_NAME)
    return _table


def _get_lambda_client() -> Any:
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client("lambda", region_name=Config.REGION)
    return _lambda_client

def _resp(code: int, obj: dict[str, Any], headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """
    Create a standardized API Gateway response.

    Builds a response dict with JSON body, appropriate headers, and status code.
    Always includes content-type and cache-control headers, with optional extras.

    Args:
        code: HTTP status code (e.g., 200, 400, 404, 500)
        obj: Response body object to be JSON-serialized
        headers: Optional additional headers to merge into response

    Returns:
        dict: API Gateway response format with statusCode, headers, and body
    """
    h = {"content-type": "application/json", "cache-control": "no-store"}
    if headers:
        h.update(headers)
    return {"statusCode": code, "headers": h, "body": json.dumps(obj)}

def _ulid() -> str:
    """
    Generate a ULID (Universally Unique Lexicographically Sortable Identifier).

    ULIDs are like UUIDs but sortable by creation time. They consist of:
    - 48-bit timestamp (milliseconds since epoch)
    - 80-bit randomness
    - Encoded in Crockford's base32 (26 characters)

    This ensures quotes are naturally sorted by creation time in DynamoDB
    when using ULID as the sort key.

    Returns:
        str: A 26-character ULID string (e.g., "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    """
    ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    timestamp_ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), 'big')
    ulid_int = (timestamp_ms << 80) | randomness

    ulid_str = ""
    for _ in range(26):
        ulid_str = ENCODING[ulid_int & 0x1F] + ulid_str
        ulid_int >>= 5

    return ulid_str

def _normalize_quote(quote_text: str) -> str:
    """
    Remove surrounding quotes from quote text to ensure consistent storage format.

    Strips leading/trailing whitespace and removes matching quote characters
    from both ends. Handles both straight quotes ("') and curly quotes (""'').

    Args:
        quote_text: Raw quote text that may include surrounding quotes

    Returns:
        str: Normalized quote text without surrounding quote characters

    Example:
        >>> _normalize_quote('"Hello world"')
        'Hello world'
        >>> _normalize_quote("'Test'")
        'Test'
    """
    text = quote_text.strip()

    quote_chars = ['"', "'", '"', '"', "'", "'"]

    for quote_char in quote_chars:
        if len(text) >= 2 and text.startswith(quote_char) and text.endswith(quote_char):
            text = text[1:-1].strip()
            break

    return text


def _invoke_page_generator() -> None:
    function_name = os.getenv("PAGE_GENERATOR_FUNCTION_NAME", "").strip()
    if not function_name:
        return

    payload = json.dumps({"source": "quotes-api"}).encode("utf-8")
    try:
        _get_lambda_client().invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=payload,
        )
    except Exception as exc:
        print(f"Failed to invoke page generator: {exc}")

def _post_quote(event: dict[str, Any], _ctx: Optional[Any]) -> dict[str, Any]:
    """
    Create a new quote and store it in DynamoDB.

    Validates quote length, checks for SQL-like content, normalizes the quote text,
    generates a ULID for the sort key, and stores in DynamoDB. It then kicks
    off the static site publisher asynchronously.

    Args:
        event: API Gateway event with JSON body containing a quote string
        _ctx: Lambda context (unused)

    Returns:
        dict: API Gateway response with:
            - 201 Created on success with quote metadata
            - 400 Bad Request on validation errors
            - 400 Bad Request on invalid JSON

    Validation:
        - Quote length must be 5-300 characters
        - Quote cannot contain SQL-like patterns
        - JSON body must be valid
    """
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return _resp(400, {"error": "Invalid JSON"})

    raw_quote = (body.get("quote") or "").strip()
    quote = _normalize_quote(raw_quote)

    n = len(quote)
    if not (Config.MIN_INPUT_LENGTH <= n <= Config.MAX_INPUT_LENGTH):
        return _resp(400, {"error": f"Quote length must be between {Config.MIN_INPUT_LENGTH} and {Config.MAX_INPUT_LENGTH}."})
    if SQLISH.search(quote):
        return _resp(400, {"error": "Input contains SQL-like content. There is no SQL here."})

    now = datetime.now(timezone.utc).isoformat()
    item = {"PK": "QUOTE", "SK": _ulid(), "quote": quote, "createdAt": now}
    _get_table().put_item(Item=item)
    _invoke_page_generator()
    return _resp(
        201,
        {
            "quoteId": item["SK"],
            "quote": quote,
            "createdAt": now,
            "url": f"/quotes/{item['SK']}/",
        },
        headers={"access-control-allow-origin": get_cors_origin()},
    )

def handler(event: dict[str, Any], ctx: Any) -> dict[str, Any]:
    """
    Lambda function entry point for the quotes API.

    Handles API Gateway requests and routes them to appropriate handlers.
    This Lambda only accepts quote submissions and CORS preflight requests.

    Args:
        event: API Gateway event payload (HTTP API v2 or REST API format)
        ctx: Lambda context object with runtime information

    Returns:
        dict: API Gateway response with statusCode, headers, and body

    Supported Routes:
        - POST /quotes: Create a new quote
        - OPTIONS /quotes: CORS preflight
    """
    return _route(event, ctx)
