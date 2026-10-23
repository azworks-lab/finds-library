#!/usr/bin/env python3
"""Safely update an existing FINDS card from a reviewed request; never create duplicates."""
import json
import ipaddress
import socket
import urllib.parse
import urllib.request
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
image_url=request.get("image_url")
if image_url is not None:
    if request.get("image_verified") is not True or not isinstance(image_url,str):
        raise SystemExit("Remote image requires image_verified=true")
    if "photo" in changes:
        raise SystemExit("Choose either photo or image_url")
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
if image_url is not None:
    parsed=urllib.parse.urlparse(image_url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
        raise SystemExit("Only public HTTPS image URLs supported")
    def public_host(host):
        if host.lower()=="localhost" or host.lower().endswith((".local",".internal")):
            return False
        try:
            addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
            return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
        except (OSError,ValueError):
            return False
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            p=urllib.parse.urlparse(newurl)
            if p.scheme!="https" or not p.hostname or not public_host(p.hostname):
                raise ValueError("Unsafe redirect")
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    if not public_host(parsed.hostname):
        raise SystemExit("Image host is not public")
    opener=urllib.request.build_opener(SafeRedirect)
    with opener.open(urllib.request.Request(image_url,headers={"User-Agent":"FINDS-image-update/1.0"}),timeout=30) as response:
        raw=response.read(8_000_001)
    if not 1000<=len(raw)<=8_000_000:
        raise SystemExit("Image size out of range")
    if raw.startswith(bytes.fromhex("ffd8ff")) and raw.endswith(bytes.fromhex("ffd9")):
        ext="jpg"
    elif raw.startswith(bytes.fromhex("89504e470d0a1a0a")) and raw[-8:-4]==b"IEND":
        ext="png"
    elif raw[:4]==b"RIFF" and raw[8:12]==b"WEBP":
        ext="webp"
    else:
        raise SystemExit("Unsupported image content")
    destination=ROOT/"images"/(pid+"-updated."+ext)
    if destination.exists():
        raise SystemExit("Refusing to overwrite existing image")
    destination.write_bytes(raw)
    changes["photo"]="images/"+destination.name
before=len(catalog["products"])
matches[0].update(changes)
if len(catalog["products"])!=before:
    raise SystemExit("Unexpected catalog size change")
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Updated",pid,"fields:",", ".join(sorted(changes)))
