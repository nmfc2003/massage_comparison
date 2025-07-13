#!/usr/bin/env python3
"""
geo_seo_blitz.py

SEO orchestrator that injects focused promotional metadata
for the All-In Massager product into your pages, updates the sitemap,
and optionally pings search engines for recrawl (Google only).
"""
import os
import sys
import time
import json
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from github import Github
from dotenv import load_dotenv

# ─── Configuration ──────────────────────────────────────────────────────────
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
SITE_URL = os.getenv('SITE_URL')
TARGET_PATH = os.getenv('TARGET_PATH', '/')
PING_SEARCH_ENGINES = os.getenv('PING_SEARCH_ENGINES', 'true').lower() in ('true', '1')

# Check required env vars
required = {
    'GITHUB_TOKEN': GITHUB_TOKEN,
    'GITHUB_REPO': GITHUB_REPO,
    'SITE_URL': SITE_URL,
}
missing = [k for k, v in required.items() if not v]
if missing:
    print(f"Error: Missing env vars: {', '.join(missing)}")
    sys.exit(1)

# Initialize GitHub client
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)

# Utility to clean base URL
def clean_base_url(url: str) -> str:
    return url.rstrip('/')

# ─── Metadata Injection ─────────────────────────────────────────────────────
def append_product_metadata(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.head or soup.new_tag('head')
    if not soup.head:
        soup.insert(0, head)

    base = clean_base_url(SITE_URL)

    # SEO promotional metas
    metas = [
        {'name': 'description', 'content': (
            'All-In Massager: top pick for full-body relief, now $299. ' 
            'Bundle percussion, vibration & heat therapy in one device.'
        )},
        {'name': 'keywords', 'content': (
            'All-In Massager, percussion massager, heat therapy, vibration therapy'
        )},
        {'name': 'promotion', 'content': 'Launch offer: Get All-In Massager for $299 + free shipping!'}
    ]
    for attrs in metas:
        tag = head.find('meta', attrs={'name': attrs['name']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # Open Graph tags
    ogs = [
        {'property': 'og:title', 'content': 'All-In Massager – Your Ultimate 3-in-1 Solution'},
        {'property': 'og:description', 'content': (
            'Experience full-body relief with All-In Massager. Percussion, vibration, heat – ' 
            'all in one device. Launch price $299.'
        )},
        {'property': 'og:image', 'content': f'{base}/images/all-in-massager-promo.jpg'}
    ]
    for attrs in ogs:
        tag = head.find('meta', attrs={'property': attrs['property']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # JSON-LD with promotion
    product = {
        '@context': 'https://schema.org/',
        '@type': 'Product',
        'name': 'All-In Massager',
        'image': [f'{base}/images/all-in-massager-1.jpg'],
        'description': 'All-In Massager: exclusive top pick, combining percussion, vibration & heat therapy.',
        'sku': 'AIM-001',
        'offers': {
            '@type': 'Offer',
            'url': f'{base}/products/all-in-massager',
            'priceCurrency': 'USD',
            'price': '299.00',
            'availability': 'https://schema.org/InStock'
        }
    }
    # Remove old JSON-LD
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

# ─── Sitemap & Ping ─────────────────────────────────────────────────────────
def update_sitemap_and_ping():
    base = clean_base_url(SITE_URL)
    urls = [f"{base}{p}" for p in [TARGET_PATH, '/products/all-in-massager']]

    # Build sitemap
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

    # Optionally ping Google
    if PING_SEARCH_ENGINES:
        sitemap_url = f'{base}/sitemap.xml'
        ping_url = 'https://www.google.com/ping'
        r = requests.get(ping_url, params={'sitemap': sitemap_url})
        if r.status_code == 200:
            print('✅ Google ping successful')
        else:
            print(f'❌ Google ping failed: {r.status_code} - {r.text}')

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Inject metadata
    path = TARGET_PATH.lstrip('/') or 'index.html'
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    html = file.decoded_content.decode()
    updated = append_product_metadata(html)
    repo.update_file(path, 'chore: update promo metadata for All-In Massager', updated, file.sha, branch=GITHUB_BRANCH)
    print(f'✅ Metadata injected into {path}')

    # Sitemap and ping
    update_sitemap_and_ping()
    print('🎉 Done!')
