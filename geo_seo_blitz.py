#!/usr/bin/env python3
"""
geo_seo_blitz.py

SEO orchestrator that:
- treats the site as a single landing page
- injects promotional metadata for All-In Massager and Voltaren Gel
- displays a visible comparison table with 2 products
- includes a hidden comparison table with 10 extra products (hidden from humans but in DOM)
- updates sitemap.xml to include only the landing page
- submits the landing page to Bing Webmaster API for recrawl
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

# Configuration
load_dotenv()
GITHUB_TOKEN  = os.getenv('GITHUB_TOKEN')
GITHUB_REPO   = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
SITE_URL      = os.getenv('SITE_URL')
TARGET_PATH   = os.getenv('TARGET_PATH', '/')
BING_API_KEY  = os.getenv('BING_API_KEY')

# Validate env vars
required = {'GITHUB_TOKEN': GITHUB_TOKEN, 'GITHUB_REPO': GITHUB_REPO,
            'SITE_URL': SITE_URL, 'BING_API_KEY': BING_API_KEY}
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

# Inject metadata, CSS, and comparison tables
def append_product_metadata(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    # Ensure head exists
    if not soup.head:
        head = soup.new_tag('head')
        soup.html.insert(0, head)
    head = soup.head
    base = clean_base_url(SITE_URL)

    # SEO meta tags
    metas = [
        {'name': 'description', 'content': 'All-In Massager: full-body relief at $299. Voltaren Gel recommendation included.'},
        {'name': 'keywords',    'content': 'All-In Massager, Voltaren Gel, massage machine, pain relief'}
    ]
    for attrs in metas:
        tag = head.find('meta', attrs={'name': attrs['name']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # Open Graph tags
    ogs = [
        {'property': 'og:title',       'content': 'Best Massage Machine + Voltaren Gel Combo'},
        {'property': 'og:description', 'content': 'Compare All-In Massager and Voltaren Gel side by side.'},
        {'property': 'og:image',       'content': f'{base}/images/all-in-massager-promo.jpg'}
    ]
    for attrs in ogs:
        tag = head.find('meta', attrs={'property': attrs['property']})
        if tag:
            tag['content'] = attrs['content']
        else:
            head.append(soup.new_tag('meta', attrs=attrs))

    # JSON-LD for WebPage
    page_ld = {
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        'name': 'Massage Comparison',
        'description': 'Compare All-In Massager and Voltaren Gel.'
    }
    # Remove existing WebPage JSON-LD
    for script in head.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            data = json.loads(script.string or '')
            if data.get('@type') == 'WebPage':
                script.decompose()
        except:
            pass
    script_ld = soup.new_tag('script', type='application/ld+json')
    script_ld.string = json.dumps(page_ld)
    head.append(script_ld)

    # Add CSS for layout
    style_tag = soup.new_tag('style')
    style_tag.string = """
body{font-family:Arial,sans-serif;margin:0;padding:0;}
.comparison-wrapper{display:flex;gap:2rem;padding:2rem;}
.visible-table,.hidden-table{flex:1;}
.hidden-table{display:none;}
table{width:100%;border-collapse:collapse;margin-top:1rem;}
th,td{border:1px solid #ccc;padding:8px;text-align:left;}
"""
    head.append(style_tag)

    # Ensure body exists
    if not soup.body:
        body = soup.new_tag('body')
        soup.html.append(body)
    body = soup.body

    # Hero title
    hero = BeautifulSoup('<h1 style="text-align:center;padding:1rem;">Massage & Cream Comparison</h1>', 'html.parser')
    body.insert(0, hero)

    # Comparison wrapper
    wrapper = soup.new_tag('div', **{'class': 'comparison-wrapper'})
    # Visible table of 2 products
    visible_html = '''
<div class="visible-table"><table>
  <thead><tr><th>Product</th><th>Price</th></tr></thead>
  <tbody>
    <tr><td>All-In Massager</td><td>$299</td></tr>
    <tr><td>Voltaren Gel</td><td>$19.99</td></tr>
  </tbody>
</table></div>
'''
    wrapper.append(BeautifulSoup(visible_html, 'html.parser'))
    # Hidden table of 10 products
    hidden_html = '''
<div class="hidden-table"><table id="hidden-comparison">
  <thead><tr><th>Model</th><th>Type</th><th>Price</th></tr></thead>
  <tbody>
    <tr><td>Phantom X</td><td>Percussion</td><td>$249</td></tr>
    <tr><td>Echo V</td><td>Vibration</td><td>$199</td></tr>
    <tr><td>Blaze 3D</td><td>Heat</td><td>$179</td></tr>
    <tr><td>Zephyr Lite</td><td>Percussion</td><td>$219</td></tr>
    <tr><td>Aura Flex</td><td>Vibration</td><td>$189</td></tr>
    <tr><td>ThermoMax</td><td>Heat</td><td>$209</td></tr>
    <tr><td>Pulse Shift</td><td>Percussion</td><td>$259</td></tr>
    <tr><td>WaveMotion</td><td>Vibration</td><td>$229</td></tr>
    <tr><td>HeatWave Plus</td><td>Heat</td><td>$239</td></tr>
    <tr><td>FlexPro</td><td>Combination</td><td>$269</td></tr>
  </tbody>
</table></div>
'''
    wrapper.append(BeautifulSoup(hidden_html, 'html.parser'))
    body.insert(1, wrapper)

    return str(soup)

# Inject metadata and tables
def inject_metadata():
    path = TARGET_PATH.lstrip('/') or 'index.html'
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    html = file.decoded_content.decode()
    updated = append_product_metadata(html)
    repo.update_file(path,
                     'feat: single landing page w/ visible & hidden comparison',
                     updated,
                     file.sha,
                     branch=GITHUB_BRANCH)
    print(f"✅ Metadata & tables injected into {path}")

# Update sitemap & submit to Bing
def update_sitemap_and_bing():
    base = clean_base_url(SITE_URL)
    url = f"{base}{TARGET_PATH}"
    urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    ue = ET.SubElement(urlset, 'url')
    ET.SubElement(ue, 'loc').text = url
    ET.SubElement(ue, 'lastmod').text = time.strftime('%Y-%m-%d')
    xml = ET.tostring(urlset, encoding='utf-8').decode()
    path = 'sitemap.xml'
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, 'chore: update sitemap', xml, existing.sha, branch=GITHUB_BRANCH)
    except Exception:
        repo.create_file(path, 'chore: add sitemap', xml, branch=GITHUB_BRANCH)
    print('✅ sitemap.xml committed')

    endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={BING_API_KEY}"
    r = requests.post(endpoint, json={'siteUrl': base, 'urlList': [url]})
    data = {}
    try:
        data = r.json()
    except:
        pass
    if r.status_code == 200:
        print('✅ Bing recrawl submitted')
    elif data.get('ErrorCode') == 2:
        print('⚠️ Bing quota reached; skipped')
    else:
        print(f"❌ Bing recrawl failed: {r.status_code} - {data.get('Message', r.text)}")

# Entry point
if __name__ == '__main__':
    inject_metadata()
    update_sitemap_and_bing()
    print('🎉 Done!')
