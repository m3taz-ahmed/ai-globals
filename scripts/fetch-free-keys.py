#!/usr/bin/env python3
"""Fetch and parse active keys from the free-llm-api-keys GitHub repository."""

import argparse
import json
import re
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/alistaitsacle/free-llm-api-keys/main/README.md"

def fetch_keys():
    try:
        req = urllib.request.Request(
            URL,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching README: {e}", file=sys.stderr)
        sys.exit(1)

    # Regex to match key rows in tables: | `sk-xxx` | model | status | budget | rate limit | expires | description |
    # Matches key, model, status, budget, rate_limit, expires, and optional description.
    pattern = re.compile(
        r'^\|\s*`(sk-[A-Za-z0-9]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|(?:\s*([^|]+?)\s*\|)?',
        re.MULTILINE
    )

    keys = []
    seen = set()
    for match in pattern.finditer(content):
        key = match.group(1).strip()
        if key in seen:
            continue
        seen.add(key)

        model = match.group(2).strip()
        status = match.group(3).strip()
        budget = match.group(4).strip()
        rate_limit = match.group(5).strip()
        expires = match.group(6).strip()
        desc = match.group(7).strip() if match.group(7) else ""

        keys.append({
            "key": key,
            "model": model,
            "status": status,
            "budget": budget,
            "rate_limit": rate_limit,
            "expires": expires,
            "description": desc
        })

    return keys

def main():
    parser = argparse.ArgumentParser(description="Fetch active keys from free-llm-api-keys repository.")
    parser.add_argument("--json", action="store_true", help="Output in JSON format.")
    parser.add_argument("--env", action="store_true", help="Output as environment variable exports.")
    args = parser.parse_args()

    keys = fetch_keys()

    if args.json:
        print(json.dumps(keys, indent=2))
        return

    if args.env:
        if not keys:
            print("# No keys available", file=sys.stderr)
            sys.exit(1)
        # Select the first smart-chat / multi-model key if available, otherwise just the first key
        selected = next((k for k in keys if "smart-chat" in k["model"]), keys[0])
        print(f"export OPENAI_API_KEY=\"{selected['key']}\"")
        print("export OPENAI_API_BASE=\"https://aiapiv2.pekpik.com/v1\"")
        return

    if not keys:
        print("No active keys found.")
        return

    # Print ASCII table
    print(f"\nActive Free LLM Keys (Fetched from {URL})")
    print("=" * 110)
    print(f"{'Key':<50} | {'Model':<22} | {'Budget':<8} | {'Rate Limit':<12} | {'Expires':<10}")
    print("-" * 110)
    for k in keys:
        print(f"{k['key']:<50} | {k['model']:<22} | {k['budget']:<8} | {k['rate_limit']:<12} | {k['expires']:<10}")
    print("=" * 110)

if __name__ == "__main__":
    main()
