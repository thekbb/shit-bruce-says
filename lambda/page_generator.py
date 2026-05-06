import html
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key


GA_MEASUREMENT_ID = "G-RR8X5VGSWX"
SITE_NAME = "Shit Bruce Says"
SITE_DESCRIPTION = (
    "A collection of memorable quotes and sayings from Bruce. "
    "Share your favorite Bruce quotes and discover what others remember him saying."
)
MAX_STRUCTURED_QUOTES = 50
HTML_CACHE_CONTROL = "public, max-age=5"
SITEMAP_CACHE_CONTROL = "public, max-age=60"

_s3_client: Any | None = None
_dynamodb_resource: Any | None = None


def get_bucket_name() -> str:
    return os.environ["BUCKET_NAME"]


def get_domain() -> str:
    return os.environ["DOMAIN"]


def get_site_base_url() -> str:
    base_url = os.environ.get("SITE_BASE_URL", "").rstrip("/")
    if base_url:
        return base_url
    return f"https://{get_domain()}"


def get_api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "").rstrip("/")


def get_table_name() -> str:
    return os.environ["TABLE_NAME"]


def get_region() -> str:
    return os.environ.get("AWS_REGION", "us-east-2")


def get_local_site_dir() -> Path | None:
    local_site_dir = os.environ.get("LOCAL_SITE_DIR", "").strip()
    if not local_site_dir:
        return None
    return Path(local_site_dir)


def get_s3_client() -> Any:
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=get_region())
    return _s3_client


def get_dynamodb_resource() -> Any:
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource(
            "dynamodb",
            region_name=get_region(),
            endpoint_url=os.environ.get("DYNAMODB_ENDPOINT"),
        )
    return _dynamodb_resource


def get_table() -> Any:
    return get_dynamodb_resource().Table(get_table_name())


def escape_html(text: str) -> str:
    return html.escape(text, quote=True)


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def format_date(iso_string: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%B %d, %Y at %H:%M:%S UTC")
    except (ValueError, AttributeError):
        return iso_string


def quote_url(quote_id: str) -> str:
    return f"{get_site_base_url()}/quotes/{quote_id}/"


def root_url() -> str:
    return f"{get_site_base_url()}/"


def analytics_script() -> str:
    return f"""  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA_MEASUREMENT_ID}');
  </script>"""


def render_json_ld(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


def render_share_buttons(quote_id: str, quote_text: str) -> str:
    escaped_text = escape_html(quote_text)
    return f"""
        <div class="share-buttons">
          <button class="share-btn" data-quote-id="{quote_id}" data-quote-text="{escaped_text}" data-platform="linkedin" title="Share on LinkedIn" type="button">
            <i class="fab fa-linkedin"></i>
          </button>
          <button class="share-btn" data-quote-id="{quote_id}" data-quote-text="{escaped_text}" data-platform="bluesky" title="Share on Bluesky" type="button">
            <i class="fas fa-cloud"></i>
          </button>
          <button class="share-btn copy-btn" data-quote-id="{quote_id}" title="Copy link" type="button">
            <i class="fas fa-link"></i>
          </button>
        </div>"""


def render_quote_card(quote: dict[str, str]) -> str:
    quote_id = quote["SK"]
    permalink = quote_url(quote_id)
    quote_text = escape_html(quote["quote"])
    display_date = format_date(quote["createdAt"])
    share_buttons = render_share_buttons(quote_id, quote["quote"])
    return f"""
        <article class="quote" id="{quote_id}">
          <h3 class="visually-hidden">Quote from {display_date}</h3>
          <blockquote cite="{permalink}">
            <p>"{quote_text}"</p>
            <footer>
              <cite>— Bruce</cite>
            </footer>
          </blockquote>
          <div class="quote-meta">
            <time class="timestamp" datetime="{quote["createdAt"]}">
              <a href="{permalink}" aria-label="Permalink to this quote">{display_date}</a>
            </time>
            {share_buttons}
          </div>
        </article>"""


def render_head(
    *,
    title: str,
    description: str,
    canonical_url: str,
    og_type: str,
    structured_data: Any,
) -> str:
    escaped_title = escape_html(title)
    escaped_description = escape_html(description)
    escaped_canonical = escape_html(canonical_url)
    api_base_url = escape_html(get_api_base_url())
    image_url = escape_html(f"{get_site_base_url()}/favicon.svg")
    return f"""<head>
  {analytics_script()}
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="api-base" content="{api_base_url}">
  <meta name="description" content="{escaped_description}">
  <meta name="author" content="{SITE_NAME}">
  <meta property="og:type" content="{escape_html(og_type)}">
  <meta property="og:url" content="{escaped_canonical}">
  <meta property="og:title" content="{escaped_title}">
  <meta property="og:description" content="{escaped_description}">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:image" content="{image_url}">
  <meta property="og:image:width" content="512">
  <meta property="og:image:height" content="512">
  <meta property="og:image:type" content="image/svg+xml">
  <meta property="og:locale" content="en_US">
  <meta property="twitter:card" content="summary">
  <meta property="twitter:url" content="{escaped_canonical}">
  <meta property="twitter:title" content="{escaped_title}">
  <meta property="twitter:description" content="{escaped_description}">
  <meta property="twitter:image" content="{image_url}">
  <link rel="canonical" href="{escaped_canonical}">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script type="application/ld+json">{render_json_ld(structured_data)}</script>
  <script src="/app.js" defer></script>
  <title>{escaped_title}</title>
</head>"""


def render_homepage(quotes: list[dict[str, str]]) -> str:
    featured_quote = quotes[0] if quotes else None
    featured_description = (
        f'"{truncate(featured_quote["quote"], 140)}" and many more memorable quotes from Bruce.'
        if featured_quote
        else SITE_DESCRIPTION
    )
    item_list = [
        {
            "@type": "ListItem",
            "position": index + 1,
            "url": quote_url(quote["SK"]),
            "name": truncate(quote["quote"], 120),
        }
        for index, quote in enumerate(quotes[:MAX_STRUCTURED_QUOTES])
    ]
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": SITE_NAME,
                "url": root_url(),
                "description": SITE_DESCRIPTION,
            },
            {
                "@type": "CollectionPage",
                "name": SITE_NAME,
                "url": root_url(),
                "description": featured_description,
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(quotes),
                    "itemListElement": item_list,
                },
            },
        ],
    }
    quote_markup = "\n".join(render_quote_card(quote) for quote in quotes)
    if not quote_markup:
        quote_markup = '<p class="empty-state">No quotes yet. Be the first to add one.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
{render_head(
    title=SITE_NAME,
    description=featured_description,
    canonical_url=root_url(),
    og_type="website",
    structured_data=structured_data,
)}
<body>
  <div id="wrapper">
    <header>
      <h1>{SITE_NAME}</h1>
      <p class="tagline">A collection of memorable quotes and sayings from Bruce</p>
    </header>

    <main>
      <section class="form" aria-label="Add a new quote">
        <h2 class="visually-hidden">Add a New Quote</h2>
        <form id="quote-form" role="form">
          <label for="quote" class="visually-hidden">Enter a Bruce quote</label>
          <input type="text" id="quote" minlength="5" maxlength="300" name="quote"
                 placeholder="What did Bruce say?" required
                 aria-describedby="quote-help" />
          <small id="quote-help" class="visually-hidden">Enter a memorable quote from Bruce (5-300 characters)</small>
          <input type="submit" value="Submit Quote"/>
        </form>
        <p id="form-status" class="form-status" aria-live="polite"></p>
      </section>

      <section class="quotes" id="quotes" aria-label="Bruce quotes" role="feed">
        <h2 class="visually-hidden">All Quotes</h2>
        {quote_markup}
      </section>
    </main>
  </div>
</body>
</html>"""


def render_quote_page(quote: dict[str, str]) -> str:
    quote_id = quote["SK"]
    canonical = quote_url(quote_id)
    title = f'"{truncate(quote["quote"], 120)}" — Bruce | {SITE_NAME}'
    description = f'"{truncate(quote["quote"], 150)}" — Bruce, said on {format_date(quote["createdAt"])}'
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Quotation",
        "text": quote["quote"],
        "creator": {
            "@type": "Person",
            "name": "Bruce",
        },
        "dateCreated": quote["createdAt"],
        "url": canonical,
        "isPartOf": {
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": root_url(),
        },
    }

    return f"""<!DOCTYPE html>
<html lang="en">
{render_head(
    title=title,
    description=description,
    canonical_url=canonical,
    og_type="article",
    structured_data=structured_data,
)}
<body>
  <div id="wrapper">
    <header>
      <h1><a href="/" style="color: inherit; text-decoration: none;">{SITE_NAME}</a></h1>
      <p class="tagline">A collection of memorable quotes and sayings from Bruce</p>
    </header>

    <main>
      <p class="page-intro"><a href="/">Back to all quotes</a></p>
      <section class="quotes" id="quotes" aria-label="Bruce quote">
        {render_quote_card(quote)}
      </section>
    </main>
  </div>
</body>
</html>"""


def render_sitemap(quotes: list[dict[str, str]]) -> str:
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quote_urls = []
    for quote in quotes:
        quote_date = quote["createdAt"][:10]
        quote_urls.append(
            f"""
    <url>
        <loc>{quote_url(quote["SK"])}</loc>
        <lastmod>{quote_date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{root_url()}</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>{''.join(quote_urls)}
</urlset>
"""


def put_html(key: str, body: str, cache_control: str = HTML_CACHE_CONTROL) -> None:
    local_site_dir = get_local_site_dir()
    if local_site_dir is not None:
        output_path = local_site_dir / key
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(body, encoding="utf-8")
        return

    get_s3_client().put_object(
        Bucket=get_bucket_name(),
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="text/html; charset=utf-8",
        CacheControl=cache_control,
    )


def put_xml(key: str, body: str) -> None:
    local_site_dir = get_local_site_dir()
    if local_site_dir is not None:
        output_path = local_site_dir / key
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(body, encoding="utf-8")
        return

    get_s3_client().put_object(
        Bucket=get_bucket_name(),
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/xml",
        CacheControl=SITEMAP_CACHE_CONTROL,
    )


def fetch_all_quotes() -> list[dict[str, str]]:
    response = get_table().query(
        KeyConditionExpression=Key("PK").eq("QUOTE"),
        ScanIndexForward=False,
    )
    quotes = list(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = get_table().query(
            KeyConditionExpression=Key("PK").eq("QUOTE"),
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        quotes.extend(response.get("Items", []))

    return quotes


def publish_site() -> dict[str, Any]:
    quotes = fetch_all_quotes()
    local_site_dir = get_local_site_dir()

    if local_site_dir is not None:
        shutil.rmtree(local_site_dir / "quotes", ignore_errors=True)
        shutil.rmtree(local_site_dir / "quote", ignore_errors=True)
        legacy_seo = local_site_dir / "seo.html"
        if legacy_seo.exists():
            legacy_seo.unlink()

    put_html("index.html", render_homepage(quotes))
    for quote in quotes:
        put_html(f"quotes/{quote['SK']}/index.html", render_quote_page(quote))
    put_xml("sitemap.xml", render_sitemap(quotes))

    return {"quoteCount": len(quotes)}


def handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    result = publish_site()
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Static site published successfully",
                "quoteCount": result["quoteCount"],
            }
        ),
    }
