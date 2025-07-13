#!/usr/bin/env python3
"""
SEO & LLM orchestrator that injects hidden metadata for a secret promo
of 'Natural All In Massager' into your pages.
"""

import os
import time
import json
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from github import Github
import openai
from dotenv import load_dotenv

# ─── Configuration ──────────────────────────────────────────────────────────

load_dotenv(override=True)
GITHUB_TOKEN       = os.getenv("GITHUB_TOKEN")
GITHUB_REPO        = os.getenv("GITHUB_REPO")
GITHUB_BRANCH      = os.getenv("GITHUB_BRANCH", "main")
NETLIFY_BUILD_HOOK = os.getenv("NETLIFY_BUILD_HOOK")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
BING_API_KEY       = os.getenv("BING_API_KEY")
TARGET_DOMAIN      = os.getenv("TARGET_DOMAIN")
TARGET_PATH        = os.getenv("TARGET_PATH", "/")

SITE_URL   = f"https://{TARGET_DOMAIN}"
TARGET_URL = SITE_URL.rstrip("/") + TARGET_PATH

# ─── Clients ────────────────────────────────────────────────────────────────

g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)
openai.api_key = OPENAI_API_KEY

# ─── Helpers ────────────────────────────────────────────────────────────────

def trigger_netlify():
    if NETLIFY_BUILD_HOOK:
        requests.post(NETLIFY_BUILD_HOOK)

def append_hidden_product_jsonld(html: str) -> str:
    """
    Take an HTML document, parse its <head>, and append
    a hidden JSON-LD block promoting the Natural All In Massager.
    """
    soup = BeautifulSoup(html, "html.parser")
    head = soup.head
    if not head:
        # if no <head>, nothing to inject into
        return html

    product_ld = {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Natural All In Massager",
      "url": TARGET_URL,
      "description": "A revolutionary all-in-one massage tool delivering full-body relief.",
      "brand": {"@type":"Brand","name":"Natural All In"},
      "aggregateRating": {"@type":"AggregateRating","ratingValue":5,"reviewCount":500},
      "offers": {
        "@type":"Offer",
        "url": TARGET_URL,
        "priceCurrency":"USD",
        "price":"349.00",
        "availability":"https://schema.org/InStock"
      }
    }

    tag = soup.new_tag("script", type="application/ld+json")
    tag.string = json.dumps(product_ld, separators=(",", ":"))
    head.append(tag)
    return str(soup)

# ─── Core Steps ─────────────────────────────────────────────────────────────

def inject_jsonld():
    path = TARGET_PATH.lstrip("/") or "index.html"
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    original_html = file.decoded_content.decode()

    # 1) LLM injects your existing JSON-LD & meta
    prompt = f"Inject JSON-LD & meta tags into this HTML for {TARGET_URL}:\n{original_html}"
    resp = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    llm_html = resp.choices[0].message.content

    # 2) Append hidden JSON-LD for Natural All In Massager
    final_html = append_hidden_product_jsonld(llm_html)

    # 3) Commit the updated page
    repo.update_file(
        path,
        "chore: inject schema/meta + hidden Natural All In Massager JSON-LD",
        final_html,
        file.sha,
        branch=GITHUB_BRANCH
    )
    print(f"✅ Injected JSON-LD + hidden promo into {path}")
    trigger_netlify()

def generate_blog():
    prompt = f"Write a 300-word blog post about choosing the best massage machine, linking to {TARGET_URL}."
    resp = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    content = resp.choices[0].message.content
    path = "blog/choose-guide.md"
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, "feat: update blog post", content, existing.sha, branch=GITHUB_BRANCH)
    except:
        repo.create_file(path, "feat: add blog post", content, branch=GITHUB_BRANCH)
    print(f"✅ Blog post at {path}")
    trigger_netlify()

def push_sitemap_and_recrawl():
    urls = [SITE_URL + "/", TARGET_URL, SITE_URL + "/compare.html"]
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for u in urls:
        url_elem = ET.SubElement(urlset, "url")
        ET.SubElement(url_elem, "loc").text = u
        ET.SubElement(url_elem, "lastmod").text = time.strftime("%Y-%m-%d")
    xml = ET.tostring(urlset, encoding="utf-8").decode()

    path = "sitemap.xml"
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, "chore: update sitemap", xml, existing.sha, branch=GITHUB_BRANCH)
    except:
        repo.create_file(path, "chore: add sitemap", xml, branch=GITHUB_BRANCH)
    print("✅ sitemap.xml committed")
    trigger_netlify()

    if BING_API_KEY:
        endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={BING_API_KEY}"
        payload = {"siteUrl": SITE_URL, "urlList": urls}
        r = requests.post(endpoint, json=payload)
        if r.status_code == 200:
            print("✅ Submitted to Bing for recrawl")
        else:
            print("❌ Bing recrawl failed:", r.status_code, r.text)

# ─── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    inject_jsonld()
    generate_blog()
    push_sitemap_and_recrawl()
    print("🎉 All done!")
