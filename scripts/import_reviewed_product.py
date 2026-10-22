#!/usr/bin/env python3
"""Import one reviewed FINDS product and its image. Never overwrite an existing ID."""
import ipaddress
import json
import pathlib
import re
import socket
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
request_file = ROOT / "data/product-import-request.json"
catalog_file = ROOT / "data/products.json"
if not request_file.exists():
    print("No product import request; nothing to do")
    raise SystemExit(0)
request = json.loads(request_file.read_text(encoding="utf-8"))
product = request.get("product")
url = request.get("image_url")
approved = request.get("image_verified")
if not isinstance(product, dict) or not isinstance(url, str) or approved is not True:
    raise SystemExit("Request requires product, image_url and image_verified=true")
pid = product.get("id")
if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,100}", pid):
    raise SystemExit("Invalid product ID")
if product.get("photo"):
    raise SystemExit("Do not set photo in import request")
required = ("name", "category", "subcategory", "status", "brand", "specs", "note", "addedAt")
for key in required:
    if not isinstance(product.get(key), str) or not product[key].strip():
        raise SystemExit("Missing product field: " + key)
if product["status"] not in ("Куплено", "Выбрано", "В комплекте", "Кандидат"):
    raise SystemExit("Invalid product status")
import datetime
if datetime.date.fromisoformat(product["addedAt"]).isoformat() != product["addedAt"]:
    raise SystemExit("Invalid addedAt date")
data = json.loads(catalog_file.read_text(encoding="utf-8"))
ids = {p["id"] for p in data["products"]}
if pid in ids:
    raise SystemExit("Existing product protected: " + pid)
if any(rid not in ids for rid in product.get("related", [])):
    raise SystemExit("Unknown related product")
parsed = urllib.parse.urlparse(url)
if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
    raise SystemExit("Only public HTTPS image URLs supported")
def public_host(host):
    if host.lower() in ("localhost",) or host.lower().endswith((".local", ".internal")):
        return False
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (OSError, ValueError):
        return False
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlparse(newurl)
        if p.scheme != "https" or not p.hostname or not public_host(p.hostname):
            raise ValueError("Unsafe redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)
if not public_host(parsed.hostname):
    raise SystemExit("Image host is not public")
opener = urllib.request.build_opener(SafeRedirect)
with opener.open(urllib.request.Request(url, headers={"User-Agent": "FINDS-image-import/1.0"}), timeout=30) as response:
    raw = response.read(8_000_001)
if not 1000 <= len(raw) <= 8_000_000:
    raise SystemExit("Image size out of range")
if raw.startswith(bytes.fromhex("ffd8ff")) and raw.endswith(bytes.fromhex("ffd9")):
    ext = "jpg"
elif raw.startswith(bytes.fromhex("89504e470d0a1a0a")) and raw[-8:-4] == b"IEND":
    ext = "png"
elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
    ext = "webp"
else:
    raise SystemExit("Unsupported or incomplete image")
destination = ROOT / "images" / (pid + "." + ext)
if destination.exists():
    raise SystemExit("Existing image file protected")
destination.write_bytes(raw)
product["photo"] = "images/" + destination.name
data["products"].append(product)
catalog_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
request_file.unlink()
print("Imported", pid, len(raw), "bytes, image:", product["photo"])
