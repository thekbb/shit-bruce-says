#!/usr/bin/env python3
"""
Generate individual quote pages for better social sharing.
Creates /quote/QUOTE123.html for each quote with specific Open Graph tags.
"""

import os
import pathlib
import requests
from datetime import datetime

def fetch_quotes(api_base, limit=100):
    """Fetch quotes from the API."""
    url = f"{api_base}/quotes?limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

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

def generate_quote_page(quote, domain="shitbrucesays.co.uk"):
    """Generate HTML for a single quote page."""
    quote_text = quote['quote']
    quote_id = quote['SK']
    created_at = quote['createdAt']

    # Truncate quote for meta description if too long
    meta_quote = quote_text if len(quote_text) <= 150 else quote_text[:147] + "..."

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>"{escape_html(quote_text)}" — Bruce | Shit Bruce Says</title>
    <meta name="description" content='"{escape_html(meta_quote)}" — Bruce, said on {format_date(created_at)}'>

    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://{domain}/quote/{quote_id}.html">
    <meta property="og:title" content=""{escape_html(quote_text)}"
— Bruce">
    <meta property="og:description" content='Said on {format_date(created_at)} | Shit Bruce Says'>
    <meta property="og:site_name" content="Shit Bruce Says">
    <meta property="og:image" content="https://{domain}/favicon.svg">
    <meta property="og:image:width" content="100">
    <meta property="og:image:height" content="100">
    <meta property="og:image:type" content="image/svg+xml">
    <meta property="og:article:published_time" content="{created_at}">
    <meta property="og:article:author" content="Bruce">

    <!-- Twitter Card (still needed for some crawlers) -->
    <meta property="twitter:card" content="summary">
    <meta property="twitter:url" content="https://{domain}/quote/{quote_id}.html">
    <meta property="twitter:title" content=""{escape_html(quote_text)}"
— Bruce">
    <meta property="twitter:description" content='Said on {format_date(created_at)} | Shit Bruce Says'>
    <meta property="twitter:image" content="https://{domain}/favicon.svg">

    <!-- Canonical URL points to main site with hash -->
    <link rel="canonical" href="https://{domain}/#{quote_id}">

    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="stylesheet" href="../styles.css">

    <!-- Redirect humans to main site after social crawlers get metadata -->
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

def main():
    domain = "shitbrucesays.co.uk"
    api_base = f"https://api.{domain}"

    print("Fetching quotes from API...")
    quotes_data = fetch_quotes(api_base, limit=200)
    quotes = quotes_data.get('items', [])

    # Create quote directory
    quote_dir = pathlib.Path("web/quote")
    quote_dir.mkdir(exist_ok=True)

    print(f"Generating {len(quotes)} individual quote pages...")

    for quote in quotes:
        quote_id = quote['SK']
        html_content = generate_quote_page(quote, domain)

        quote_file = quote_dir / f"{quote_id}.html"
        quote_file.write_text(html_content)

        print(f"  Generated: quote/{quote_id}.html")

    print(f"✓ Generated {len(quotes)} quote pages in web/quote/")
    print("Deploy with: terraform apply")

if __name__ == '__main__':
    main()
