#!/usr/bin/env python3
"""Read-only checks for FINDS V2 product catalog and local images."""
import datetime
import json
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
errors = []
warnings = []
def fail(message):
    errors.append(message)

try:
    data = json.loads((root / "data/products.json").read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    raise SystemExit(f"FAIL: Cannot read products.json: {exc}")

if data.get("version") != "2.0":
    fail("Unexpected catalog version")
items = data.get("products")
if not isinstance(items, list):
    raise SystemExit("FAIL: products must be a list")
ids = [p.get("id") for p in items if isinstance(p, dict)]
if len(ids) != len(items):
    fail("Non-object product entry")
if len(ids) != len(set(ids)):
    fail("Duplicate product ID")
known = set(ids)
statuses = {"Куплено", "Выбрано", "В комплекте", "Кандидат"}
local_count = remote_count = 0
for item in items:
    if not isinstance(item, dict):
        continue
    pid = item.get("id") or "<missing>"
    for key in ("id", "name", "category", "subcategory", "status", "brand", "specs", "note"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            fail(f"{pid}: missing {key}")
    if item.get("status") not in statuses:
        fail(f"{pid}: unknown status")
    if "addedAt" in item:
        try:
            datetime.date.fromisoformat(item["addedAt"])
            if len(item["addedAt"]) != 10:
                raise ValueError("not YYYY-MM-DD")
        except (ValueError, TypeError):
            fail(f"{pid}: invalid addedAt")
    for related in item.get("related", []):
        if related not in known:
            fail(f"{pid}: broken related ID {related}")
    photo = item.get("photo")
    if not isinstance(photo, str) or not photo:
        fail(f"{pid}: missing photo")
    elif photo.startswith("images/"):
        rel = Path(photo)
        if ".." in rel.parts or rel.is_absolute():
            fail(f"{pid}: unsafe photo path")
            continue
        image = root / rel
        if not image.is_file() or image.stat().st_size == 0:
            fail(f"{pid}: missing/empty image {photo}")
        else:
            with image.open("rb") as stream:
                signature = stream.read(12)
            if not (signature.startswith(bytes.fromhex("ffd8ff")) or
                    signature.startswith(bytes.fromhex("89504e470d0a1a0a")) or
                    (signature[:4] == b"RIFF" and signature[8:12] == b"WEBP")):
                fail(f"{pid}: unsupported image signature {photo}")
        local_count += 1
    elif photo.startswith("https://"):
        remote_count += 1
        parsed = urlparse(photo)
        if parsed.hostname != "raw.githubusercontent.com":
            warnings.append(f"{pid}: remote image host not checked: {parsed.hostname}")
    else:
        fail(f"{pid}: unsupported photo path/URL")
print(f"FINDS V2: {len(items)} products, {local_count} local images, {remote_count} remote image URLs")
for warning in warnings:
    print("WARN:", warning)
for error in errors:
    print("FAIL:", error)
if errors:
    raise SystemExit(f"FAIL: {len(errors)} issue(s)")
print("PASS: catalog structure, IDs, relationships, dates and local image files")
