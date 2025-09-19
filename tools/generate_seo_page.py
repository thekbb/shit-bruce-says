#!/usr/bin/env python3
"""
Generate a static HTML page with quotes for SEO.
This creates a server-rendered version with the latest quotes embedded.

Usage:
    python generate_seo_page.py --output web/seo.html --limit 50
    python generate_seo_page.py --production  # Use production API
"""

import argparse
import json
import pathlib
import requests
from datetime import datetime
from urllib.parse import quote

def escape_html(text):
    """Escape HTML characters."""
    return (text.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;")
               .replace("'", "&#039;"))

def format_date(iso_string):
    """Format ISO date for display."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y at %H:%M:%S')
    except:
        return iso_string

def fetch_quotes(api_base, limit=50):
    """Fetch quotes from the API."""
    url = f"{api_base}/quotes?limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def generate_quote_html(quote):
    """Generate HTML for a single quote."""
    return f'''
    <article class="quote" id="{quote['SK']}">
        <h3 class="visually-hidden">Quote from {format_date(quote['createdAt'])}</h3>
        <blockquote cite="#{quote['SK']}">
            <p>"{escape_html(quote['quote'])}"</p>
            <footer>
                <cite>— Bruce</cite>
            </footer>
        </blockquote>
        <time class="timestamp" datetime="{quote['createdAt']}">
            <a href="#{quote['SK']}" aria-label="Link to this quote">{format_date(quote['createdAt'])}</a>
        </time>
    </article>'''

def generate_seo_page(quotes_data, domain="shitbrucesays.co.uk"):
    """Generate the complete SEO-optimized HTML page."""
    quotes = quotes_data.get('items', [])
    quote_count = len(quotes)

    # Generate quote HTML
    quotes_html = '\n'.join(generate_quote_html(quote) for quote in quotes)

    # Create structured data for SEO
    structured_data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Shit Bruce Says",
        "description": "A collection of memorable quotes and sayings from Bruce",
        "url": f"https://{domain}",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": quote_count,
            "itemListElement": [
                {
                    "@type": "Quotation",
                    "text": quote['quote'],
                    "datePublished": quote['createdAt'],
                    "author": {
                        "@type": "Person",
                        "name": "Bruce"
                    }
                } for quote in quotes[:10]  # Limit structured data to first 10
            ]
        }
    }

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shit Bruce Says - {quote_count} Memorable Quotes</title>
    <meta name="description" content="Collection of {quote_count} memorable quotes and sayings from Bruce. Funny, insightful, and quotable moments.">
    <meta name="keywords" content="Bruce quotes, sayings, memorable quotes, funny quotes, Bruce sayings">
    <meta name="author" content="Shit Bruce Says">

    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://{domain}/">
    <meta property="og:title" content="Shit Bruce Says - {quote_count} Memorable Quotes">
    <meta property="og:description" content="Collection of {quote_count} memorable quotes and sayings from Bruce. Funny, insightful, and quotable moments.">
    <meta property="og:site_name" content="Shit Bruce Says">
    <meta property="og:image" content="https://{domain}/favicon.svg">

    <!-- Structured Data -->
    <script type="application/ld+json">
    {json.dumps(structured_data, indent=2)}
    </script>

    <link rel="canonical" href="https://{domain}/">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="stylesheet" href="styles.css">

    <!-- Redirect to interactive version after page load for better UX -->
    <script>
        // Let search engines crawl, then redirect users to interactive version
        if (!navigator.userAgent.includes('bot') && !navigator.userAgent.includes('crawler')) {{
            setTimeout(() => {{
                if (!window.location.hash) {{ // Don't redirect if user is viewing specific quote
                    window.location.href = '/';
                }}
            }}, 2000);
        }}
    </script>
</head>
<body>
    <div id="wrapper">
        <header>
            <h1>Shit Bruce Says</h1>
            <p class="tagline">A collection of memorable quotes and sayings from Bruce</p>
            <p class="seo-notice">
                <a href="/">Click here for the interactive version</a> where you can add new quotes!
            </p>
        </header>

        <main>
            <section class="quotes" aria-label="Bruce quotes">
                <h2>All Quotes ({quote_count} total)</h2>
                {quotes_html}
            </section>
        </main>

        <footer>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | <a href="/">Interactive Version</a></p>
        </footer>
    </div>
</body>
</html>'''

def main():
    parser = argparse.ArgumentParser(description='Generate SEO-optimized static page with quotes')
    parser.add_argument('--output', default='web/seo.html', help='Output file path')
    parser.add_argument('--limit', type=int, default=100, help='Number of quotes to include')
    parser.add_argument('--domain', default='shitbrucesays.co.uk', help='Domain name for URLs')

    args = parser.parse_args()

    api_base = f"https://api.{args.domain}"

    try:
        print(f"Fetching {args.limit} quotes from {api_base}...")
        quotes_data = fetch_quotes(api_base, args.limit)

        print(f"Generating SEO page with {len(quotes_data.get('items', []))} quotes...")
        html_content = generate_seo_page(quotes_data, args.domain)

        # Write to file
        output_path = pathlib.Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content)

        # Generate fresh sitemap.xml
        current_date = datetime.now().strftime('%Y-%m-%d')
        sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://{args.domain}/</loc>
    <lastmod>2025-01-01</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>

  <url>
    <loc>https://{args.domain}/seo.html</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
'''

        sitemap_path = pathlib.Path("web/sitemap.xml")
        sitemap_path.write_text(sitemap_content)
        print(f"✓ Generated sitemap.xml with current date: {current_date}")

        print(f"✓ Generated SEO page: {output_path}")
        print(f"  - {len(quotes_data.get('items', []))} quotes included")
        print(f"  - Structured data for first 10 quotes")
        print(f"  - Canonical URL: https://{args.domain}/")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
