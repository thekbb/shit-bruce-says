import os
import sys

import boto3
import pytest
from moto import mock_aws

# Ensure the module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import page_generator  # noqa: E402


def _create_table():
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
    dynamodb.create_table(
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
    return dynamodb.Table(os.environ["TABLE_NAME"])


def _create_bucket():
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    s3.create_bucket(
        Bucket=os.environ["BUCKET_NAME"],
        CreateBucketConfiguration={"LocationConstraint": os.environ["AWS_REGION"]},
    )
    return s3


@pytest.fixture(autouse=True)
def env_vars():
    os.environ["AWS_REGION"] = "us-east-2"
    os.environ["TABLE_NAME"] = "bruce-quotes"
    os.environ["BUCKET_NAME"] = "bruce-quotes-site-test"
    os.environ["DOMAIN"] = "shitbrucesays.co.uk"
    os.environ["API_BASE_URL"] = "https://api.shitbrucesays.co.uk"
    os.environ.pop("LOCAL_SITE_DIR", None)
    os.environ.pop("SITE_BASE_URL", None)
    if hasattr(page_generator, "_s3_client"):
        page_generator._s3_client = None
    if hasattr(page_generator, "_dynamodb_resource"):
        page_generator._dynamodb_resource = None
    yield


@mock_aws
def test_publish_site_generates_home_quote_pages_and_sitemap():
    table = _create_table()
    s3 = _create_bucket()
    table.put_item(
        Item={
            "PK": "QUOTE",
            "SK": "01JABCDEF1234567890ABCDEF",
            "quote": "Bruce said the thing",
            "createdAt": "2026-05-05T12:00:00+00:00",
        }
    )

    result = page_generator.publish_site()

    assert result["quoteCount"] == 1

    homepage = s3.get_object(Bucket=os.environ["BUCKET_NAME"], Key="index.html")
    homepage_body = homepage["Body"].read().decode("utf-8")
    assert "Bruce said the thing" in homepage_body
    assert 'href="https://shitbrucesays.co.uk/quotes/01JABCDEF1234567890ABCDEF/"' in homepage_body
    assert 'meta name="api-base" content="https://api.shitbrucesays.co.uk"' in homepage_body
    assert homepage["CacheControl"] == page_generator.HTML_CACHE_CONTROL

    quote_page = s3.get_object(
        Bucket=os.environ["BUCKET_NAME"],
        Key="quotes/01JABCDEF1234567890ABCDEF/index.html",
    )
    quote_body = quote_page["Body"].read().decode("utf-8")
    assert "Back to all quotes" in quote_body
    assert 'rel="canonical" href="https://shitbrucesays.co.uk/quotes/01JABCDEF1234567890ABCDEF/"' in quote_body

    sitemap = s3.get_object(Bucket=os.environ["BUCKET_NAME"], Key="sitemap.xml")
    sitemap_body = sitemap["Body"].read().decode("utf-8")
    assert "https://shitbrucesays.co.uk/quotes/01JABCDEF1234567890ABCDEF/" in sitemap_body


@mock_aws
def test_publish_site_handles_empty_database():
    _create_table()
    s3 = _create_bucket()

    result = page_generator.publish_site()

    assert result["quoteCount"] == 0

    homepage = s3.get_object(Bucket=os.environ["BUCKET_NAME"], Key="index.html")
    homepage_body = homepage["Body"].read().decode("utf-8")
    assert "No quotes yet. Be the first to add one." in homepage_body

    sitemap = s3.get_object(Bucket=os.environ["BUCKET_NAME"], Key="sitemap.xml")
    sitemap_body = sitemap["Body"].read().decode("utf-8")
    assert "<loc>https://shitbrucesays.co.uk/</loc>" in sitemap_body


@mock_aws
def test_publish_site_can_write_to_local_directory(tmp_path):
    table = _create_table()
    table.put_item(
        Item={
            "PK": "QUOTE",
            "SK": "01JLOCAL1234567890ABCDEF0",
            "quote": "Local Bruce quote",
            "createdAt": "2026-05-05T12:00:00+00:00",
        }
    )
    os.environ["LOCAL_SITE_DIR"] = str(tmp_path)
    os.environ["SITE_BASE_URL"] = "http://localhost:8080"

    result = page_generator.publish_site()

    assert result["quoteCount"] == 1
    homepage = (tmp_path / "index.html").read_text(encoding="utf-8")
    quote_page = (tmp_path / "quotes" / "01JLOCAL1234567890ABCDEF0" / "index.html").read_text(encoding="utf-8")
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")

    assert "Local Bruce quote" in homepage
    assert 'meta name="api-base" content="https://api.shitbrucesays.co.uk"' in homepage
    assert 'href="http://localhost:8080/quotes/01JLOCAL1234567890ABCDEF0/"' in homepage
    assert "Back to all quotes" in quote_page
    assert "<loc>http://localhost:8080/quotes/01JLOCAL1234567890ABCDEF0/</loc>" in sitemap
