import os
import json
import sys
from datetime import datetime, timezone, timedelta

import boto3
import pytest
from moto import mock_aws

# Ensure the app module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app  # noqa: E402


def _mk_table():
    ddb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
    ddb.create_table(
        TableName=os.environ["TABLE_NAME"],
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
    )
    return ddb.Table(os.environ["TABLE_NAME"])


@pytest.fixture(autouse=True)
def env_vars():
    os.environ["AWS_REGION"] = "us-east-2"
    os.environ["TABLE_NAME"] = "bruce-quotes"
    # reset lazy table singleton between tests
    if hasattr(app, "_table"):
        app._table = None
    yield


@mock_aws
def test_post_and_get_quotes():
    _mk_table()

    post_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "Cowabunga, Bruce!"}),
    }
    post_resp = app.handler(post_event, None)
    assert post_resp["statusCode"] == 201
    assert post_resp["headers"]["access-control-allow-origin"] == "*"
    assert post_resp["headers"]["content-type"] == "application/json"
    assert "no-store" in post_resp["headers"]["cache-control"]

    get_event = {"requestContext": {"http": {"method": "GET", "path": "/quotes"}}}
    get_resp = app.handler(get_event, None)
    assert get_resp["statusCode"] == 200
    body = json.loads(get_resp["body"])
    assert len(body["items"]) == 1
    assert body["items"][0]["quote"] == "Cowabunga, Bruce!"


@mock_aws
def test_reject_sqlish():
    _mk_table()

    post_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "select * from bruce where 1=1;"}),
    }
    resp = app.handler(post_event, None)
    assert resp["statusCode"] == 400
    assert "SQL-like" in json.loads(resp["body"])["error"]


@mock_aws
def test_length_validation():
    _mk_table()

    # Too short
    ev_short = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "hey"}),  # len=3 < 5
    }
    r1 = app.handler(ev_short, None)
    assert r1["statusCode"] == 400

    # Too long
    ev_long = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "x" * 301}),
    }
    r2 = app.handler(ev_long, None)
    assert r2["statusCode"] == 400


@mock_aws
def test_bad_json_body():
    _mk_table()

    ev = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": "{not json}",
    }
    r = app.handler(ev, None)
    assert r["statusCode"] == 400
    assert "Invalid JSON" in json.loads(r["body"])["error"]


@mock_aws
def test_options_cors_preflight():
    _mk_table()

    ev = {"requestContext": {"http": {"method": "OPTIONS", "path": "/quotes"}}}
    r = app.handler(ev, None)
    assert r["statusCode"] == 204
    h = r["headers"]
    assert h["access-control-allow-origin"] == "*"
    assert "GET" in h["access-control-allow-methods"]
    assert "POST" in h["access-control-allow-methods"]
    assert "content-type" in h["access-control-allow-headers"]


@mock_aws
def test_not_found_route():
    _mk_table()

    ev = {"requestContext": {"http": {"method": "GET", "path": "/nope"}}}
    r = app.handler(ev, None)
    assert r["statusCode"] == 404


@mock_aws
def test_pagination_cursor_descending_order():
    # Prepare three items with ascending SKs; query uses descending (newest first)
    tbl = _mk_table()

    now = datetime.now(timezone.utc)
    def put(sk_suffix: str, text: str, dt):
        item = {
            "PK": "QUOTE",
            # 26-char ULID-ish; using valid Base32 chars '0','1','2' is fine for lexicographic tests
            "SK": "0000000000000000000000000" + sk_suffix,  # 25 zeros + suffix -> 26 chars total
            "quote": text,
            "createdAt": dt.isoformat()
        }
        tbl.put_item(Item=item)

    put("0", "first",  now - timedelta(seconds=2))
    put("1", "second", now - timedelta(seconds=1))
    put("2", "third",  now)

    # Page 1: limit=2 -> expect "third","second"
    ev1 = {
        "requestContext": {"http": {"method": "GET", "path": "/quotes"}},
        "queryStringParameters": {"limit": "2"},
    }
    r1 = app.handler(ev1, None)
    assert r1["statusCode"] == 200
    b1 = json.loads(r1["body"])
    assert [it["quote"] for it in b1["items"]] == ["third", "second"]
    assert b1["cursor"] is not None

    # Page 2: use cursor -> expect "first"
    ev2 = {
        "requestContext": {"http": {"method": "GET", "path": "/quotes"}},
        "queryStringParameters": {"cursor": json.dumps(b1["cursor"])},
    }
    r2 = app.handler(ev2, None)
    assert r2["statusCode"] == 200
    b2 = json.loads(r2["body"])
    assert [it["quote"] for it in b2["items"]] == ["first"]
