import json
import boto3
import os
from datetime import datetime
from typing import Dict, List, Any

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
DOMAIN = os.environ['DOMAIN']
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function entry point triggered by DynamoDB Streams.

    Processes INSERT/MODIFY events for quotes and generates:
    - Individual quote page (quote/{id}.html)
    - SEO landing page (seo.html)
    - Sitemap (sitemap.xml)

    Args:
        event: DynamoDB Stream event containing Records array
        context: Lambda context object with runtime information

    Returns:
        dict: Response with statusCode 200 and success message
    """
    print(f"Received event: {json.dumps(event, default=str)}")

    records = event.get('Records', [])

    for record in records:
        event_name = record.get('eventName')

        if event_name in ['INSERT', 'MODIFY']:
            dynamodb_record = record.get('dynamodb', {})
            new_image = dynamodb_record.get('NewImage', {})

            if new_image and new_image.get('PK', {}).get('S') == 'QUOTE':
                quote_id = new_image.get('SK', {}).get('S')
                print(f"Processing quote: {quote_id}")

                generate_quote_page(new_image)
                generate_seo_page()

    return {'statusCode': 200, 'body': json.dumps('Pages generated successfully')}

def dynamodb_to_dict(dynamodb_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DynamoDB Stream item format to plain dictionary.

    Extracts values from DynamoDB's typed format (e.g., {'S': 'value'})
    into a simple Python dict with native types.

    Args:
        dynamodb_item: DynamoDB item in Stream format with typed attributes

    Returns:
        dict: Plain dictionary with string/number/binary values
    """
    result = {}
    for key, value in dynamodb_item.items():
        if 'S' in value:
            result[key] = value['S']
        elif 'N' in value:
            result[key] = float(value['N'])
        elif 'B' in value:
            result[key] = value['B']
    return result

def escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS.

    Replaces &, <, >, ", and ' with their HTML entity equivalents.

    Args:
        text: Raw text that may contain HTML special characters

    Returns:
        str: HTML-safe text with escaped characters
    """
    return (text.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;")
               .replace("'", "&#039;"))

def format_date(iso_string: str) -> str:
    """
    Format ISO 8601 datetime string to human-readable format.

    Converts timestamps like "2024-01-15T10:30:00Z" to
    "January 15, 2024 at 10:30:00".

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        str: Human-readable date string, or original if parsing fails
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y at %H:%M:%S')
    except (ValueError, AttributeError):
        return iso_string

def generate_quote_page(dynamodb_item: Dict[str, Any]) -> None:
    """
    Generate individual HTML page for a single quote.

    Creates a static HTML page optimized for social media sharing with
    Open Graph and Twitter Card meta tags. The page automatically redirects
    non-bot traffic to the main site but serves full HTML to crawlers.

    Args:
        dynamodb_item: DynamoDB Stream item containing quote data

    Side Effects:
        Uploads quote/{quote_id}.html to S3 bucket
    """
    quote = dynamodb_to_dict(dynamodb_item)
    quote_text = quote['quote']
    quote_id = quote['SK']
    created_at = quote['createdAt']
    meta_quote = quote_text if len(quote_text) <= 150 else quote_text[:147] + "..."

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>"{escape_html(quote_text)}" — Bruce | Shit Bruce Says</title>
    <meta name="description" content='"{escape_html(meta_quote)}" — Bruce, said on {format_date(created_at)}'>

    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://{DOMAIN}/quote/{quote_id}.html">
    <meta property="og:title" content=""{escape_html(quote_text)}"
— Bruce">
    <meta property="og:description" content='Said on {format_date(created_at)} | Shit Bruce Says'>
    <meta property="og:site_name" content="Shit Bruce Says">
    <meta property="og:image" content="https://{DOMAIN}/favicon.svg">
    <meta property="og:image:width" content="100">
    <meta property="og:image:height" content="100">
    <meta property="og:image:type" content="image/svg+xml">
    <meta property="og:article:published_time" content="{created_at}">
    <meta property="og:article:author" content="Bruce">

    <!-- Twitter Card -->
    <meta property="twitter:card" content="summary">
    <meta property="twitter:url" content="https://{DOMAIN}/quote/{quote_id}.html">
    <meta property="twitter:title" content=""{escape_html(quote_text)}"
— Bruce">
    <meta property="twitter:description" content='Said on {format_date(created_at)} | Shit Bruce Says'>
    <meta property="twitter:image" content="https://{DOMAIN}/favicon.svg">

    <link rel="canonical" href="https://{DOMAIN}/#{quote_id}">

    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="stylesheet" href="../styles.css">

    <script>
        if (!navigator.userAgent.includes('bot') &&
            !navigator.userAgent.includes('crawler') &&
            !navigator.userAgent.includes('facebookexternalhit') &&
            !navigator.userAgent.includes('LinkedInBot') &&
            !navigator.userAgent.includes('Twitterbot')) {{
            setTimeout(() => {{
                window.location.href = '/#{quote_id}';
            }}, 1000);
        }}
    </script>
</head>
<body>
    <div id="wrapper">
        <header>
            <h1>Shit Bruce Says</h1>
            <p class="tagline">A collection of memorable quotes and sayings from Bruce</p>
        </header>

        <main>
            <article class="quote" id="{quote_id}">
                <h2 class="visually-hidden">Quote from {format_date(created_at)}</h2>
                <blockquote cite="#{quote_id}">
                    <p>"{escape_html(quote_text)}"</p>
                    <footer>
                        <cite>— Bruce</cite>
                    </footer>
                </blockquote>
                <time class="timestamp" datetime="{created_at}">
                    <a href="/#{quote_id}" aria-label="Link to this quote">{format_date(created_at)}</a>
                </time>
            </article>

            <p style="margin-top: 2rem; text-align: center;">
                <a href="/" style="background: #007acc; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 4px;">
                    View All Quotes & Add New Ones
                </a>
            </p>
        </main>
    </div>
</body>
</html>'''

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=f'quote/{quote_id}.html',
        Body=html_content,
        ContentType='text/html; charset=utf-8',
        CacheControl='public, max-age=86400'
    )

    print(f"Generated quote page: quote/{quote_id}.html")

def fetch_all_quotes() -> List[Dict[str, Any]]:
    """
    Fetch all quotes from DynamoDB in reverse chronological order.

    Handles pagination automatically by following LastEvaluatedKey tokens
    until all quotes are retrieved. Loads all quotes into memory.

    Returns:
        list: All quote dictionaries sorted newest-first, each containing:
            - PK: Partition key (always "QUOTE")
            - SK: Sort key (ULID timestamp identifier)
            - quote: Quote text
            - createdAt: ISO 8601 timestamp
    """
    table = dynamodb.Table(TABLE_NAME)
    quotes = []

    response = table.query(
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={':pk': 'QUOTE'},
        ScanIndexForward=False
    )

    quotes.extend(response['Items'])

    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': 'QUOTE'},
            ScanIndexForward=False,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        quotes.extend(response['Items'])

    return quotes

def generate_seo_page() -> None:
    """
    Generate SEO landing page and sitemap for all quotes.

    Creates two files:
    - seo.html: Static landing page with all quotes for SEO/indexing
    - sitemap.xml: XML sitemap with all quote URLs for search engines

    Includes structured data (JSON-LD), Open Graph tags, and properly
    formatted HTML for maximum SEO value.

    Side Effects:
        Uploads seo.html and sitemap.xml to S3 bucket
    """
    quotes = fetch_all_quotes()

    if not quotes:
        print("No quotes found for SEO page")
        return

    featured_quote = quotes[0] if quotes else None
    current_date = datetime.now().strftime('%Y-%m-%d')

    item_list: List[Dict[str, Any]] = []

    for i, quote in enumerate(quotes[:50]):
        item_list.append({
            "@type": "ListItem",
            "position": i + 1,
            "item": {
                "@type": "Quotation",
                "text": quote['quote'],
                "author": {
                    "@type": "Person",
                    "name": "Bruce"
                },
                "dateCreated": quote['createdAt'],
                "url": f"https://{DOMAIN}/#{quote['SK']}"
            }
        })

    structured_data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Shit Bruce Says",
        "url": f"https://{DOMAIN}/",
        "description": "A collection of memorable quotes and sayings from Bruce",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(quotes),
            "itemListElement": item_list
        }
    }

    quotes_html = ""
    for quote in quotes:
        quotes_html += f'''
        <article class="quote" id="{quote['SK']}">
            <blockquote cite="#{quote['SK']}">
                <p>"{escape_html(quote['quote'])}"</p>
                <footer>
                    <cite>— Bruce</cite>
                </footer>
            </blockquote>
            <time class="timestamp" datetime="{quote['createdAt']}">
                <a href="/#{quote['SK']}" aria-label="Link to this quote">{format_date(quote['createdAt'])}</a>
            </time>
        </article>'''

    featured_description = f'"{escape_html(featured_quote["quote"])}" and many more memorable quotes from Bruce.' if featured_quote else "Discover hilarious and memorable quotes from Bruce. New quotes added regularly by the community."

    seo_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shit Bruce Says - Memorable Quotes and Sayings</title>
    <meta name="description" content="{featured_description}">

    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://{DOMAIN}/">
    <meta property="og:title" content="Shit Bruce Says">
    <meta property="og:description" content="Discover hilarious and memorable quotes from Bruce. New quotes added regularly by the community.">
    <meta property="og:site_name" content="Shit Bruce Says">
    <meta property="og:image" content="https://{DOMAIN}/favicon.svg">
    <meta property="og:image:width" content="100">
    <meta property="og:image:height" content="100">
    <meta property="og:image:type" content="image/svg+xml">
    <meta property="og:locale" content="en_US">

    <!-- Twitter Card -->
    <meta property="twitter:card" content="summary">
    <meta property="twitter:url" content="https://{DOMAIN}/">
    <meta property="twitter:title" content="Shit Bruce Says">
    <meta property="twitter:description" content="{featured_description}">
    <meta property="twitter:image" content="https://{DOMAIN}/favicon.svg">

    <!-- Canonical URL -->
    <link rel="canonical" href="https://{DOMAIN}/">

    <!-- Structured Data -->
    <script type="application/ld+json">
{json.dumps(structured_data, indent=2)}
    </script>

    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="stylesheet" href="styles.css">

    <!-- Redirect to main app after 2 seconds -->
    <script>
        setTimeout(() => {{
            window.location.href = '/';
        }}, 2000);
    </script>
</head>
<body>
    <div id="wrapper">
        <header>
            <h1>Shit Bruce Says</h1>
            <p class="tagline">A collection of memorable quotes and sayings from Bruce</p>
        </header>

        <main>
            <p style="text-align: center; margin-bottom: 2rem;">
                <strong>Loading the interactive app...</strong>
            </p>

            {quotes_html}
        </main>
    </div>
</body>
</html>'''

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key='seo.html',
        Body=seo_html,
        ContentType='text/html; charset=utf-8',
        CacheControl='public, max-age=86400'
    )

    quote_urls = ""
    for quote in quotes:
        quote_date = quote['createdAt'][:10]
        quote_urls += f'''
    <url>
        <loc>https://{DOMAIN}/quote/{quote['SK']}.html</loc>
        <lastmod>{quote_date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>'''

    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://{DOMAIN}/</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://{DOMAIN}/seo.html</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>{quote_urls}
</urlset>
'''

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key='sitemap.xml',
        Body=sitemap_xml,
        ContentType='application/xml',
        CacheControl='public, max-age=86400'
    )

    print(f"Generated SEO page with {len(quotes)} quotes and sitemap")
