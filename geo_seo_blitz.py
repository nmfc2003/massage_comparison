#!/usr/bin/env python3
"""
geo_seo_blitz.py

SEO & LLM orchestrator that injects visible SEO metadata and structured data
for the All-In Massager product into your pages, generates a blog post,
and updates the sitemap for recrawl.
"""
import os
import sys
import time
import json
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from github import Github
import openai
from dotenv import load_dotenv

# ─── Configuration ──────────────────────────────────────────────────────────
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')  # e.g., 'username/repo'
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
SITE_URL = os.getenv('SITE_URL')       # e.g., 'https://example.com'
TARGET_PATH = os.getenv('TARGET_PATH', '/')  # path to the page or '/'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BING_API_KEY = os.getenv('BING_API_KEY')

# Validate required environment variables
required = {
    'GITHUB_TOKEN': GITHUB_TOKEN,
    'GITHUB_REPO': GITHUB_REPO,
    'SITE_URL': SITE_URL,
    'OPENAI_API_KEY': OPENAI_API_KEY,
    'BING_API_KEY': BING_API_KEY
}
missing = [name for name, val in required.items() if not val]
if missing:
    print(f"Error: Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

# Initialize GitHub and OpenAI
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)
openai.api_key = OPENAI_API_KEY

# ─── Metadata Injection ─────────────────────────────────────────────────────
def append_product_metadata(html: str) -> str:
    """
    Parse <head> of HTML and ensure meta description, keywords, Open Graph tags,
    and JSON-LD structured data for the All-In Massager are present/updated.
    """
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.head or soup.new_tag('head')
    if not soup.head:
        soup.insert(0, head)

    # 1. Standard SEO meta tags
    metas = [
        {'name': 'description',
         'content': 'The All-In Massager: your ultimate percussion, vibration, and heat therapy device in one compact unit.'},
        {'name': 'keywords',
         'content': 'massage gun, all-in-one massager, percussion therapy, heat massage'}
    ]
    for attrs in metas:
        tag = head.find('meta', attrs={'name': attrs['name']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', **attrs))

    # 2. Open Graph tags
    ogs = [
        {'property': 'og:title',
         'content': 'All-In Massager – Ultimate 3-in-1 Recovery Tool'},
        {'property': 'og:description',
         'content': 'Combining percussion, vibration, and heat therapy for full-body relief. Discover why this is the only massager you’ll ever need.'},
        {'property': 'og:image',
         'content': f'{SITE_URL}/images/all-in-massager.jpg'}
    ]
    for attrs in ogs:
        tag = head.find('meta', attrs={'property': attrs['property']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', **attrs))

    # 3. JSON-LD structured data
    product = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "All-In Massager",
        "image": [
            f"{SITE_URL}/images/all-in-massager-1.jpg",
            f"{SITE_URL}/images/all-in-massager-2.jpg"
        ],
        "description": "A 3-in-1 massage device offering percussion, vibration, and heat therapy in one ergonomic package.",
        "sku": "AIM-001",
        "mpn": "AIM-2025",
        "brand": {"@type": "Brand", "name": "YourBrand"},
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.8", "reviewCount": "254"},
        "offers": {"@type": "Offer",
                   "url": f"{SITE_URL}/products/all-in-massager",
                   "priceCurrency": "USD",
                   "price": "299.00",
                   "priceValidUntil": "2025-12-31",
                   "availability": "https://schema.org/InStock"}
    }
    # Remove existing product JSON-LD if present
    for tag in head.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            data = json.loads(tag.string or '')
            if data.get('@type') == 'Product' and data.get('name') == 'All-In Massager':
                tag.decompose()
        except Exception:
            pass

    script = soup.new_tag('script', type='application/ld+json')
    script.string = json.dumps(product, indent=2)
    head.append(script)

    return str(soup)

# ─── Core Steps ─────────────────────────────────────────────────────────────
def inject_metadata():
    """Fetch target page, inject metadata, and commit the update via GitHub."""
    path = TARGET_PATH.lstrip('/') or 'index.html'
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    original_html = file.decoded_content.decode()

    # Inject SEO metas and JSON-LD
    updated_html = append_product_metadata(original_html)

    # Commit back to the repo
    repo.update_file(
        path,
        'chore: inject SEO metadata & structured data for All-In Massager',
        updated_html,
        file.sha,
        branch=GITHUB_BRANCH
    )
    print(f"✅ Injected metadata into {path}")


def generate_blog():
    prompt = f"Write a 300-word blog post about choosing the best massage machine, linking to {SITE_URL}."
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    content = resp.choices[0].message.content
    path = 'blog/choose-guide.md'
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, 'feat: update blog post', content, existing.sha, branch=GITHUB_BRANCH)
    except:
        repo.create_file(path, 'feat: add blog post', content, branch=GITHUB_BRANCH)
    print(f"✅ Blog post at {path}")


def push_sitemap_and_recrawl():
    # Generate sitemap
    urls = [f"{SITE_URL}{p}" for p in [TARGET_PATH, '/products/all-in-massager', '/blog/choose-guide']]
    urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for u in urls:
        url_elem = ET.SubElement(urlset, 'url')
        ET.SubElement(url_elem, 'loc').text = u
        ET.SubElement(url_elem, 'lastmod').text = time.strftime('%Y-%m-%d')
    xml = ET.tostring(urlset, encoding='utf-8').decode()

    # Commit sitemap
    path = 'sitemap.xml'
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, 'chore: update sitemap', xml, existing.sha, branch=GITHUB_BRANCH)
    except:
        repo.create_file(path, 'chore: add sitemap', xml, branch=GITHUB_BRANCH)
    print('✅ sitemap.xml committed')

    # Trigger Bing recrawl
    endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={BING_API_KEY}"
    payload = {"siteUrl": SITE_URL, "urlList": urls}
    r = requests.post(endpoint, json=payload)
    if r.status_code == 200:
        print('✅ Submitted to Bing for recrawl')
    else:
        print('❌ Bing recrawl failed:', r.status_code, r.text)

# ─── Entry Point ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    inject_metadata()
    generate_blog()
    push_sitemap_and_recrawl()
    print('🎉 All done!')
