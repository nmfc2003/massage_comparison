#!/usr/bin/env python3
"""SEO & LLM orchestration for Massage Machine Comparison site."""

import os, time, requests
import xml.etree.ElementTree as ET
from github import Github
import openai
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
NETLIFY_BUILD_HOOK = os.getenv("NETLIFY_BUILD_HOOK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN")
TARGET_PATH = os.getenv("TARGET_PATH", "/")
SITE_URL = f"https://{TARGET_DOMAIN}"
TARGET_URL = SITE_URL.rstrip('/') + TARGET_PATH

# Clients
g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)
openai.api_key = OPENAI_API_KEY

def trigger_netlify():
    if NETLIFY_BUILD_HOOK:
        requests.post(NETLIFY_BUILD_HOOK)

def inject_jsonld():
    path = TARGET_PATH.lstrip('/') or 'index.html'
    file = repo.get_contents(path, ref=GITHUB_BRANCH)
    html = file.decoded_content.decode()
    prompt = f"Inject JSON-LD & meta tags into this HTML for {TARGET_URL}:\n{html}"
    resp = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}]
    )
    updated = resp.choices[0].message.content
    repo.update_file(path, "chore: inject schema/meta", updated, file.sha, branch=GITHUB_BRANCH)
    trigger_netlify()

def generate_blog():
    prompt = f"Write a 300-word blog post about choosing the best massage machine and link to {TARGET_URL}."
    resp = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}]
    )
    content = resp.choices[0].message.content
    path = "blog/choose-guide.md"
    try:
        f = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, "feat: update blog post", content, f.sha, branch=GITHUB_BRANCH)
    except:
        repo.create_file(path, "feat: add blog post", content, branch=GITHUB_BRANCH)
    trigger_netlify()

def push_sitemap_and_recrawl():
    urls = [SITE_URL + "/", TARGET_URL, SITE_URL + "/compare.html"]
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for u in urls:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = u
        ET.SubElement(url, "lastmod").text = time.strftime("%Y-%m-%d")
    xml = ET.tostring(urlset, encoding="utf-8").decode()
    path = "sitemap.xml"
    try:
        f = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, "chore: update sitemap", xml, f.sha, branch=GITHUB_BRANCH)
    except:
        repo.create_file(path, "chore: add sitemap", xml, branch=GITHUB_BRANCH)
    trigger_netlify()
    if BING_API_KEY:
        endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey={BING_API_KEY}"
        payload = {"siteUrl": SITE_URL, "urlList": urls}
        r = requests.post(endpoint, json=payload)
        print("✅ Bing recrawl" if r.status_code == 200 else f"❌ Bing recrawl {r.status_code} {r.text}")

if __name__ == '__main__':
    inject_jsonld()
    generate_blog()
    push_sitemap_and_recrawl()
    print("🎉 Complete")
