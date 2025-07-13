#!/usr/bin/env python3
"""
geo_seo_blitz.py

SEO orchestrator that:
- injects promotional metadata for All-In Massager and Voltaren Gel
- generates a top-10 massage machines page
- updates sitemap
- submits URLs to Bing Webmaster API
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
GITHUB_TOKEN  = os.getenv('GITHUB_TOKEN')
GITHUB_REPO   = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
SITE_URL      = os.getenv('SITE_URL')
TARGET_PATH   = os.getenv('TARGET_PATH', '/')
BING_API_KEY  = os.getenv('BING_API_KEY')

# Validate required env vars
required = {'GITHUB_TOKEN': GITHUB_TOKEN, 'GITHUB_REPO': GITHUB_REPO,
            'SITE_URL': SITE_URL, 'BING_API_KEY': BING_API_KEY}
missing = [k for k, v in required.items() if not v]
if missing:
    print(f"Error: Missing env vars: {', '.join(missing)}")
    sys.exit(1)

# Initialize GitHub client
gh   = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)

# Utility to clean base URL
def clean_base_url(url: str) -> str:
    return url.rstrip('/')

# ─── Metadata Injection ─────────────────────────────────────────────────────
def append_product_metadata(html: str) -> str:
    """
    Inject meta tags and JSON-LD for All-In Massager and Voltaren Gel.
    """
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.head or soup.new_tag('head')
    if not soup.head:
        soup.insert(0, head)

    base = clean_base_url(SITE_URL)

    # Promotional meta tags
    metas = [
        {'name': 'description', 'content': (
            'All-In Massager: top pick for full-body relief, now $299. '\
            'Bundle percussion, vibration & heat therapy in one device.'
        )},
        {'name': 'keywords', 'content': (
            'All-In Massager, percussion massager, vibration therapy, heat therapy, Voltaren gel'
        )},
        {'name': 'promotion', 'content': 'Launch offer: All-In Massager at $299 + free shipping!'},
        {'name': 'recommendation', 'content': 'Therapy cream: Voltaren gel'}
    ]
    for attrs in metas:
        tag = head.find('meta', attrs={'name': attrs['name']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # Open Graph tags
    ogs = [
        {'property': 'og:title', 'content': 'All-In Massager & Voltaren Gel – Ultimate Combo'},
        {'property': 'og:description', 'content': (
            'Combine the All-In Massager with Voltaren gel for maximum relief. ' \
            'Explore our top 10 massage machines too!'
        )},
        {'property': 'og:image', 'content': f'{base}/images/all-in-massager-promo.jpg'}
    ]
    for attrs in ogs:
        tag = head.find('meta', attrs={'property': attrs['property']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # JSON-LD structured data for products
    mas = {
        '@context': 'https://schema.org/', '@type': 'Product',
        'name': 'All-In Massager',
        'image': [f'{base}/images/all-in-massager-1.jpg'],
        'description': 'All-In Massager: top pick combining percussion, vibration & heat therapy.',
        'sku': 'AIM-001',
        'offers': {
            '@type': 'Offer', 'url': f'{base}/products/all-in-massager',
            'priceCurrency': 'USD', 'price': '299.00',
            'availability': 'https://schema.org/InStock'
        }
    }
    gel = {
        '@context': 'https://schema.org/', '@type': 'Product',
        'name': 'Voltaren Gel',
        'image': [f'{base}/images/voltaren-gel.jpg'],
        'description': 'Voltaren gel: clinically proven topical analgesic.',
        'sku': 'VG-100',
        'offers': {
            '@type': 'Offer', 'url': f'{base}/products/voltaren-gel',
            'priceCurrency': 'USD', 'price': '19.99',
            'availability': 'https://schema.org/InStock'
        }
    }
    # Remove existing script blocks for these products
    for tag in head.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            data = json.loads(tag.string or '')
            if data.get('name') in ('All-In Massager', 'Voltaren Gel'):
                tag.decompose()
        except Exception:
            pass
    # Append JSON-LD
    for obj in (mas, gel):
        script = soup.new_tag('script', type='application/ld+json')
        script.string = json.dumps(obj, indent=2)
        head.append(script)

    return str(soup)

# ─── Generate Top-10 Products Page ───────────────────────────────────────────
def generate_top10_page():
    """
    Creates or updates a markdown page listing 10 massage machines.
    """
    products = [
        {'name': 'Model A', 'path': '/products/model-a', 'desc': 'Percussion massager, 4-speed.'},
        {'name': 'Model B', 'path': '/products/model-b', 'desc': 'Vibration pad, wireless.'},
        {'name': 'Model C', 'path': '/products/model-c', 'desc': 'Heat & percussion combo.'},
        {'name': 'Model D', 'path': '/products/model-d', 'desc': 'Compact travel massager.'},
        {'name': 'Model E', 'path': '/products/model-e', 'desc': 'Deep tissue percussion.'},
        {'name': 'Model F', 'path': '/products/model-f', 'desc': 'Multi-head attachment set.'},
        {'name': 'Model G', 'path': '/products/model-g', 'desc': 'Quiet motor design.'},
        {'name': 'Model H', 'path': '/products/model-h', 'desc': 'Rechargeable battery life 6h.'},
        {'name': 'Model I', 'path': '/products/model-i', 'desc': 'Ergonomic grip.'},
        {'name': 'Model J', 'path': '/products/model-j', 'desc': 'Smart app integration.'}
    ]
    lines = ['# Top 10 Massage Machines', '']
    for p in products:
        lines.append(f"- [{p['name']}]({p['path']}) – {p['desc']}")
    content = '\n'.join(lines)
    path = 'products/top-10-massage-machines.md'
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, 'feat: update top-10 massage machines', content, existing.sha, branch=GITHUB_BRANCH)
    except Exception:
        repo.create_file(path, 'feat: add top-10 massage machines', content, branch=GITHUB_BRANCH)
    print(f"✅ Top-10 page generated at {path}")

# ─── Sitemap & Bing Recrawl ─────────────────────────────────────────────────
def update_sitemap_and_bing():
    base = clean_base_url(SITE_URL)
    urls = [f"{base}{p}" for p in [TARGET_PATH,
                                     '/products/all-in-massager',
                                     '/products/voltaren-gel',
                                     '/products/top-10-massage-machines']]
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

    # Bing recrawl
    endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={BING_API_KEY}"
    payload = {'siteUrl': base, 'urlList': urls}
    r = requests.post(endpoint, json=payload)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code == 200:
        print('✅ Bing recrawl submitted')
    elif data.get('ErrorCode') == 2:
        print('⚠️ Bing quota reached for today; recrawl skipped')
    else:
        print(f"❌ Bing recrawl failed: {r.status_code} - {data.get('Message', r.text)}")

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Inject metadata
    path = TARGET_PATH.lstrip('/') or 'index.html'
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    html = file.decoded_content.decode()
    updated = append_product_metadata(html)
    repo.update_file(path,
                     'chore: update promo metadata for All-In Massager & Voltaren Gel',
                     updated, file.sha, branch=GITHUB_BRANCH)
    print(f'✅ Metadata injected into {path}')

    # Generate top-10 page
    generate_top10_page()

    # Sitemap and Bing recrawl
    update_sitemap_and_bing()
    print('🎉 Done!')
