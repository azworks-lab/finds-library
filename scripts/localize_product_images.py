#!/usr/bin/env python3
"""Save externally hosted FINDS product photos into the repository."""
import io
import json
import pathlib
import urllib.parse
import urllib.request
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/products.json"
IMAGES = ROOT / "images"
MAX_BYTES = 8 * 1024 * 1024

def main():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    changed = 0
    IMAGES.mkdir(exist_ok=True)
    for product in data.get("products", []):
        url = product.get("photo", "")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            continue
        name = "".join(c if c.isascii() and (c.isalnum() or c in "-_") else "-" for c in product["id"]).strip("-")
        target = IMAGES / (name + ".jpg")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FINDS-image-import/1.0", "Accept": "image/*"})
            with urllib.request.urlopen(request, timeout=20) as response:
                if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                    raise ValueError("Response is not an image")
                blob = response.read(MAX_BYTES + 1)
            if len(blob) > MAX_BYTES:
                raise ValueError("Image exceeds 8 MB")
            with Image.open(io.BytesIO(blob)) as im:
                im.verify()
            with Image.open(io.BytesIO(blob)) as im:
                im.convert("RGB").save(target, "JPEG", quality=88, optimize=True)
            product["photo"] = "images/" + target.name
            changed += 1
            print(f"Saved {product['id']} -> {product['photo']}")
        except Exception as exc:
            print(f"Skipped {product['id']}: {exc}")
    if changed:
        CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Localized {changed} product images")

if __name__ == "__main__":
    main()
