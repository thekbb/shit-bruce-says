import json
import os
import sys
from unittest.mock import Mock

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
    os.environ.pop("ALLOW_ORIGIN", None)
    os.environ.pop("PAGE_GENERATOR_FUNCTION_NAME", None)
    if hasattr(app, "_table"):
        app._table = None
    if hasattr(app, "_lambda_client"):
        app._lambda_client = None
    yield


@mock_aws
def test_post_quote_returns_metadata_and_invokes_publisher():
    table = _mk_table()
    os.environ["PAGE_GENERATOR_FUNCTION_NAME"] = "bruce-page-generator"
    lambda_client = Mock()
    app._lambda_client = lambda_client

    post_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": '"Cowabunga, Bruce!"'}),
    }
    response = app.handler(post_event, None)

    assert response["statusCode"] == 201
    assert response["headers"]["access-control-allow-origin"] == "*"
    assert response["headers"]["content-type"] == "application/json"
    assert "no-store" in response["headers"]["cache-control"]

    body = json.loads(response["body"])
    assert body["quote"] == "Cowabunga, Bruce!"
    assert body["quoteId"]
    assert body["url"] == f"/quotes/{body['quoteId']}/"

    stored = table.get_item(Key={"PK": "QUOTE", "SK": body["quoteId"]})["Item"]
    assert stored["quote"] == "Cowabunga, Bruce!"

    lambda_client.invoke.assert_called_once()
    invoke_kwargs = lambda_client.invoke.call_args.kwargs
    assert invoke_kwargs["FunctionName"] == "bruce-page-generator"
    assert invoke_kwargs["InvocationType"] == "Event"


@mock_aws
def test_post_quote_succeeds_when_publisher_is_not_configured():
    _mk_table()

    post_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "Cowabunga, Bruce!"}),
    }
    response = app.handler(post_event, None)

    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["quote"] == "Cowabunga, Bruce!"


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

    short_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "hey"}),
    }
    assert app.handler(short_event, None)["statusCode"] == 400

    long_event = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": json.dumps({"quote": "x" * 301}),
    }
    assert app.handler(long_event, None)["statusCode"] == 400


@mock_aws
def test_bad_json_body():
    _mk_table()

    ev = {
        "requestContext": {"http": {"method": "POST", "path": "/quotes"}},
        "body": "{not json}",
    }
    response = app.handler(ev, None)
    assert response["statusCode"] == 400
    assert "Invalid JSON" in json.loads(response["body"])["error"]


@mock_aws
def test_options_cors_preflight():
    _mk_table()

    ev = {"requestContext": {"http": {"method": "OPTIONS", "path": "/quotes"}}}
    response = app.handler(ev, None)
    assert response["statusCode"] == 204
    headers = response["headers"]
    assert headers["access-control-allow-origin"] == "*"
    assert "POST" in headers["access-control-allow-methods"]
    assert "OPTIONS" in headers["access-control-allow-methods"]
    assert "content-type" in headers["access-control-allow-headers"]


@mock_aws
def test_not_found_route():
    _mk_table()

    ev = {"requestContext": {"http": {"method": "GET", "path": "/nope"}}}
    response = app.handler(ev, None)
    assert response["statusCode"] == 404


@mock_aws
def test_cors_origin_override():
    _mk_table()
    os.environ["ALLOW_ORIGIN"] = "https://shitbrucesays.co.uk"

    ev = {"requestContext": {"http": {"method": "OPTIONS", "path": "/quotes"}}}
    response = app.handler(ev, None)
    assert response["statusCode"] == 204
    assert response["headers"]["access-control-allow-origin"] == "https://shitbrucesays.co.uk"
