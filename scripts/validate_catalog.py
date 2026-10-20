#!/usr/bin/env python3
"""Validate Finds Library v2 catalog before publication."""
import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "data" / "products.json"
data = json.loads(path.read_text(encoding="utf-8"))
assert data.get("version") == "2.0", "Unsupported catalog version"
items = data.get("products")
assert isinstance(items, list), "products must be a list"
ids = set()
for i, item in enumerate(items, 1):
    for key in ("id", "name", "category", "subcategory", "status", "brand", "specs", "note"):
        assert isinstance(item.get(key), str) and item[key].strip(), f"Item {i}: missing {key}"
    assert item["id"] not in ids, f"Duplicate ID: {item['id']}"
    ids.add(item["id"])
    assert item["status"] in {"Куплено", "Выбрано"}, f"Invalid status: {item['id']}"
    if "url" in item:
        assert item["url"].startswith("https://"), f"Invalid URL: {item['id']}"
    if "imageUrl" in item:
        assert item["imageUrl"].startswith("https://"), f"Invalid image URL: {item['id']}"
    if "priceHistory" in item:
        assert isinstance(item["priceHistory"], list), f"Invalid price history: {item['id']}"
        for row in item["priceHistory"]:
            assert isinstance(row.get("date"), str) and isinstance(row.get("price"), str), f"Invalid price entry: {item['id']}"
print(f"OK: {len(items)} approved products; all IDs unique; statuses valid.")
