#!/usr/bin/env python3
"""Generate public, JavaScript-free FINDS product pages from the existing catalog."""
import html
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://finds.lv"
OUT = ROOT / "p"

def esc(value):
    return html.escape(str(value), quote=True)

def url_for(pid, lang):
    return f"{BASE}/{'en/' if lang == 'en' else ''}p/{quote(pid)}/"

def image_url(path):
    if not path:
        return ""
    return path if path.startswith("https://") else BASE + "/" + path.lstrip("/")

def generate(p, translated, lang):
    pid = p["id"]
    name = translated.get("name") or p["name"]
    description = translated.get("specs") or p.get("specs") or translated.get("preview") or p.get("preview") or ""
    brand = p.get("brand") or ""
    sku = p.get("sku") or p.get("model") or ""
    category = p.get("category") or ""
    status = p.get("status") or ""
    photo = image_url(p.get("photo"))
    canonical = url_for(pid, lang)
    details = translated.get("details") or p.get("details") or []
    title = f"{name} — FINDS"
    heading = "Specifications" if lang == "en" else "Технические характеристики"
    labels = {"brand": "Brand", "sku": "SKU", "category": "Category", "status": "Status"} if lang == "en" else {"brand": "Бренд", "sku": "Артикул", "category": "Категория", "status": "Статус"}
    rows = [(labels["brand"], brand), (labels["sku"], sku), (labels["category"], category), (labels["status"], status)]
    rows.extend((d.get("label", ""), d.get("value", "")) for d in details if isinstance(d, dict))
    rows_html = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows if k and v)
    manufacturer = p.get("manufacturerUrl") or ""
    manufacturer_html = f'<p><a href="{esc(manufacturer)}" rel="noopener noreferrer">Manufacturer</a></p>' if manufacturer.startswith("https://") else ""
    image_html = f'<img src="{esc(photo)}" alt="{esc(name)}" width="480" loading="eager">' if photo else ""
    schema = {"@context": "https://schema.org", "@type": "Product", "name": name, "description": description, "url": canonical}
    if brand:
        schema["brand"] = {"@type": "Brand", "name": brand}
    if sku:
        schema["sku"] = sku
    if photo:
        schema["image"] = photo
    # No private notes, inferred offers, purchase history or internal fields.
    jsonld = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
    altlang = "ru" if lang == "en" else "en"
    html_text = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" hreflang="ru" href="{esc(url_for(pid, 'ru'))}">
<link rel="alternate" hreflang="en" href="{esc(url_for(pid, 'en'))}">
<meta property="og:type" content="product"><meta property="og:title" content="{esc(name)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
{f'<meta property="og:image" content="{esc(photo)}">' if photo else ''}
<script type="application/ld+json">{jsonld}</script>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#101827;color:#eef2f8;margin:0}}main{{max-width:760px;margin:auto;padding:24px}}a{{color:#a9c7f8}}img{{max-width:100%;height:auto;background:white;border-radius:16px}}dl{{display:grid;grid-template-columns:minmax(120px,35%) 1fr;gap:12px}}dt{{color:#aebcd0}}dd{{margin:0;overflow-wrap:anywhere}}h1{{line-height:1.2}}</style></head>
<body><main><p><a href="{BASE}/?product={quote(pid)}">FINDS</a> · <a href="{esc(url_for(pid, altlang))}">{altlang.upper()}</a></p>
<h1>{esc(name)}</h1><p>{esc(description)}</p>{image_html}
<h2>{heading}</h2><dl>{rows_html}</dl>{manufacturer_html}</main></body></html>
"""
    destination = ROOT / ("en" if lang == "en" else "") / "p" / pid / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html_text, encoding="utf-8")

def main():
    catalog = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
    english = json.loads((ROOT / "data/products.en.json").read_text(encoding="utf-8")).get("products", {})
    ids = set()
    for p in catalog["products"]:
        pid = p["id"]
        if not pid or not all(c.isascii() and (c.isalnum() or c in "-_") for c in pid):
            raise ValueError(f"Invalid product id: {pid}")
        ids.add(pid)
        generate(p, {}, "ru")
        generate(p, english.get(pid, {}), "en")
    for folder in (ROOT / "p", ROOT / "en" / "p"):
        for page in folder.glob("*/index.html"):
            if page.parent.name not in ids:
                page.unlink()
                page.parent.rmdir()
    # Search-engine discovery: canonical RU and EN URLs only.
    # Deterministic output, no lastmod dates invented from build time.
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for pid in sorted(ids):
        for lang in ("ru", "en"):
            sitemap.append(f'  <url><loc>{esc(url_for(pid, lang))}</loc></url>')
    sitemap.append('</urlset>')
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    print(f"Generated {len(ids)} product pages in each language")

if __name__ == "__main__":
    main()
