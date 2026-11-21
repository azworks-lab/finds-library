#!/usr/bin/env python3
"""Smoke-test FINDS static pages without external dependencies."""
import importlib.util
import json
import re
import tempfile
from pathlib import Path

source = Path(__file__).with_name("generate_product_pages.py")
spec = importlib.util.spec_from_file_location("finds_generator", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = source.resolve().parents[1]
catalog = json.loads((root / "data/products.json").read_text(encoding="utf-8"))["products"]
english = json.loads((root / "data/products.en.json").read_text(encoding="utf-8"))["products"]
assert len(catalog) == len({p["id"] for p in catalog}), "Duplicate product IDs"
assert all(p["id"] in english for p in catalog), "Missing English translations"
with tempfile.TemporaryDirectory() as folder:
    module.ROOT = Path(folder)
    for p in catalog:
        for lang, trans in (("ru", {}), ("en", english[p["id"]])):
            module.generate(p, trans, lang)
            file = module.ROOT / ("en" if lang == "en" else "") / "p" / p["id"] / "index.html"
            page = file.read_text(encoding="utf-8")
            assert p["id"] in page, p["id"]
            assert '<meta name="description"' in page, p["id"]
            assert '<link rel="canonical"' in page, p["id"]
            assert '<meta property="og:title"' in page, p["id"]
            assert 'application/ld+json' in page, p["id"]
            assert "fetch(" not in page, p["id"]
            assert "<dt>" in page, p["id"]
            assert p.get("note", "<<<none>>>") not in page or not p.get("note"), "Note exposed"
            match = re.search(r'<script type="application/ld\\+json">(.*?)</script>', page, re.S)
            assert match, p["id"]
            structured = json.loads(match.group(1))
            assert structured["@type"] == "Product"
    target = module.ROOT / "p/videx-gx53-8w-3000k-hallway/index.html"
    assert target.exists(), "Control product missing"
    assert "VIDEX" in target.read_text(encoding="utf-8").upper()
    assert not (module.ROOT / "p/nonexistent-product/index.html").exists()
print(f"Validated {len(catalog) * 2} static HTML pages")
