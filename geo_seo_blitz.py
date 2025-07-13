#!/usr/bin/env python3
"""
geo_seo_blitz.py

SEO orchestrator that injects focused promotional metadata
for the All-In Massager product into your pages, updates the sitemap,
and submits URLs to Bing with improved error logging.
"""
import os
import sys
import time
import json
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from github import Github
from openai import OpenAI
from dotenv import load_dotenv

# ─── Configuration ──────────────────────────────────────────────────────────
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
SITE_URL = os.getenv('SITE_URL')
TARGET_PATH = os.getenv('TARGET_PATH', '/')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BING_API_KEY = os.getenv('BING_API_KEY')

# Check required env vars
required = {'GITHUB_TOKEN': GITHUB_TOKEN, 'GITHUB_REPO': GITHUB_REPO,
            'SITE_URL': SITE_URL, 'OPENAI_API_KEY': OPENAI_API_KEY,
            'BING_API_KEY': BING_API_KEY}
missing = [k for k, v in required.items() if not v]
if missing:
    print(f"Error: Missing env vars: {', '.join(missing)}")
    sys.exit(1)

# Initialize clients
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Utility to clean base URL
def clean_base_url(url: str) -> str:
    return url.rstrip('/')

# ─── Metadata Injection ─────────────────────────────────────────────────────
def append_product_metadata(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.head or soup.new_tag('head')
    if not soup.head:
        soup.insert(0, head)

    # Promotional SEO meta tags
    metas = [
        {'name': 'description', 'content': (
            'All-In Massager is our top pick for full-body relief—now available '
            'at $299. Combines percussion, vibration, and heat therapy in one device.'
        )},
        {'name': 'keywords', 'content': (
            'All-In Massager, top pick, full-body relief, percussion massager, '
            'vibration therapy, heat therapy, massage gun'
        )},
        {'name': 'promotion', 'content': 'Launch offer: Get the All-In Massager at $299 with free shipping.'}
    ]
    for attrs in metas:
        tag = head.find('meta', attrs={'name': attrs['name']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # Open Graph tags
    base = clean_base_url(SITE_URL)
    ogs = [
        {'property': 'og:title', 'content': 'All-In Massager – Our Top Pick for Full-Body Relief'},
        {'property': 'og:description', 'content': (
            'Discover why the All-In Massager is rated best: combines percussion, '
            'vibration, and heat therapy in one compact device. Limited-time offer!'
        )},
        {'property': 'og:image', 'content': f'{base}/images/all-in-massager-promo.jpg'}
    ]
    for attrs in ogs:
        tag = head.find('meta', attrs={'property': attrs['property']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # JSON-LD structured data with promotion
    product = {
        '@context': 'https://schema.org/', '@type': 'Product',
        'name': 'All-In Massager',
        'image': [f'{base}/images/all-in-massager-1.jpg', f'{base}/images/all-in-massager-2.jpg'],
        'description': 'All-In Massager: our exclusive top pick, combining percussion, vibration, and heat therapy.',
        'sku': 'AIM-001', 'brand': {'@type': 'Brand', 'name': 'YourBrand'},
        'offers': {
            '@type': 'Offer', 'url': f'{base}/products/all-in-massager',
            'priceCurrency': 'USD', 'price': '299.00', 'priceValidUntil': '2025-12-31',
            'availability': 'https://schema.org/InStock'
        }
    }
    # Remove existing Product JSON-LD
    for tag in head.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            data = json.loads(tag.string or '')
            if data.get('@type') == 'Product' and data.get('name') == 'All-In Massager':
                tag.decompose()
        except Exception:
            pass
    # Append new JSON-LD
    script = soup.new_tag('script', type='application/ld+json')
    script.string = json.dumps(product, indent=2)
    head.append(script)

    return str(soup)

# ─── Core Workflow ───────────────────────────────────────────────────────────
def inject_metadata():
    path = TARGET_PATH.lstrip('/') or 'index.html'
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    html = file.decoded_content.decode()
    updated = append_product_metadata(html)
    repo.update_file(path,
                     'chore: updated promotional metadata for All-In Massager',
                     updated, file.sha, branch=GITHUB_BRANCH)
    print(f"✅ Metadata injected into {path}")


def push_sitemap_and_recrawl():
    base = clean_base_url(SITE_URL)
    urls = [f"{base}{p}" for p in [TARGET_PATH, '/products/all-in-massager']]
    # Generate sitemap XML
    urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for u in urls:
        ue = ET.SubElement(urlset, 'url')
        ET.SubElement(ue, 'loc').text = u
        ET.SubElement(ue, 'lastmod').text = time.strftime('%Y-%m-%d')
    xml = ET.tostring(urlset, encoding='utf-8').decode()
    # Commit sitemap
    path = 'sitemap.xml'
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, 'chore: update sitemap', xml, existing.sha, branch=GITHUB_BRANCH)
    except Exception:
        repo.create_file(path, 'chore: add sitemap', xml, branch=GITHUB_BRANCH)
    print('✅ sitemap.xml committed')

    # Submit to Bing and log full response
    endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={BING_API_KEY}"
    payload = {'siteUrl': base, 'urlList': urls}
    r = requests.post(endpoint, json=payload)
    if r.ok:
        print('✅ Submitted to Bing for recrawl')
    else:
        print(f"❌ Bing recrawl failed: {r.status_code} - {r.text}")

if __name__ == '__main__':
    inject_metadata()
    push_sitemap_and_recrawl()
    print('🎉 Done!')
