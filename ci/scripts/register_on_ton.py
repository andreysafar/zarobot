#!/usr/bin/env python3
"""
Register skill on TON blockchain via Core API.
Future: direct on-chain registration via NFT/Toncast DAO.
"""

import argparse
import json
import sys
import urllib.request


def register_skill(registry_url: str, token: str, manifest: dict):
    """Register a skill via Core API publish endpoint."""
    payload = json.dumps({
        "name": manifest["name"],
        "display_name": manifest["display_name"],
        "description": manifest["description"],
        "version": manifest["version"],
        "creator_telegram": manifest.get("author", {}).get("name", ""),
        "category": manifest.get("category", "other"),
        "category_icon": manifest.get("category_icon", ""),
        "price_ia_coins": manifest.get("pricing", {}).get("price_ia_coins", 0),
        "is_free": manifest.get("pricing", {}).get("is_free", True),
        "pricing_model": manifest.get("pricing", {}).get("model", "one_time"),
        "tags": manifest.get("tags", []),
        "requirements": manifest.get("requirements", []),
        "config_schema": manifest.get("config_schema", {}),
        "execution_type": manifest.get("execution_type", "api_call"),
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{registry_url}/api/v1/marketplace/skills/publish/",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(json.dumps({"ok": True, "result": result}, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(json.dumps({"ok": False, "error": str(e), "body": body}))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    register_skill(args.registry_url, args.token, manifest)
