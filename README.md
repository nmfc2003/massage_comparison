# Massage Machine Comparison Site

This repository contains a multi-page static site for comparing massage machines, plus an SEO/LLM orchestration script.

## Pages
- **index.html**: Homepage overview of top massage machines.
- **compare.html**: Side-by-side comparison table of selected models.
- **products/model-a.html**: Detail page for Model A.
- **products/model-b.html**: Detail page for Model B.
- **blog/**: Folder for supporting blog posts (empty by default).

## Setup

1. **Clone or unzip** this folder to your machine.
2. **Create & activate** a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
3. **Install dependencies**:
   ```bash
   pip install PyGithub openai python-dotenv requests
   ```
4. **Copy** `.env_sample` to `.env` and fill in your credentials and target domain.

## Usage

Run the SEO & LLM orchestration script to:
1. Inject JSON-LD and meta tags into all pages.
2. Generate supporting blog posts via LLM.
3. Regenerate `sitemap.xml` and push to GitHub.
4. Trigger Netlify deploy and submit URLs to Bing for recrawl.

```bash
python geo_seo_blitz.py
```

Replace prompts in `geo_seo_blitz.py` as needed for your product pages and blog topics.
