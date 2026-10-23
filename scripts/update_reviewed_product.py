#!/usr/bin/env python3
"""Safely update an existing FINDS card from a reviewed request; never create duplicates."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
catalog_path=ROOT/"data/products.json"
request_path=ROOT/"data/product-update-request.json"
if not request_path.exists():
    print("No update request")
    raise SystemExit(0)
request=json.loads(request_path.read_text(encoding="utf-8"))
pid=request.get("id")
changes=request.get("changes")
if not isinstance(pid,str) or not isinstance(changes,dict) or not changes:
    raise SystemExit("Expected existing id and nonempty changes")
allowed={"specs","note","tags","details","manufacturerUrl","sku","photo"}
if not set(changes)<=allowed:
    raise SystemExit("Unapproved update fields: "+repr(set(changes)-allowed))
catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
matches=[p for p in catalog["products"] if p.get("id")==pid]
if len(matches)!=1:
    raise SystemExit("Expected exactly one existing product with id "+pid)
if "photo" in changes:
    path=changes["photo"]
    if not isinstance(path,str) or not path.startswith("images/") or ".." in Path(path).parts:
        raise SystemExit("Invalid local image path")
    image=ROOT/path
    if not image.is_file() or image.stat().st_size==0:
        raise SystemExit("Photo does not exist")
for key,value in changes.items():
    if key in {"specs","note","manufacturerUrl","sku","photo"} and (not isinstance(value,str) or not value.strip()):
        raise SystemExit("Invalid text: "+key)
    if key in {"tags","details"} and not isinstance(value,list):
        raise SystemExit("Invalid list: "+key)
before=len(catalog["products"])
matches[0].update(changes)
if len(catalog["products"])!=before:
    raise SystemExit("Unexpected catalog size change")
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Updated",pid,"fields:",", ".join(sorted(changes)))
