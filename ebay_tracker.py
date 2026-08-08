import json
import os
import re
import base64
from datetime import datetime, timezone

import requests


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

CLIENT_ID = os.environ["EBAY_CLIENT_ID"]
CLIENT_SECRET = os.environ["EBAY_CLIENT_SECRET"]

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

MARKETPLACE_ID = "EBAY_US"


# ------------------------------------------------------------
# Get eBay application access token
# ------------------------------------------------------------

def get_access_token():
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


# ------------------------------------------------------------
# Determine whether a listing matches a given watch config
# ------------------------------------------------------------

def is_valid_listing(item, watch_config):
    title = item.get("title", "").lower()

    # Exclude terms
    for term in watch_config.get("exclude_terms", []):
        if term in title:
            return False

    # Must contain brand
    if watch_config.get("brand", "").lower() not in title:
        return False

    # Must contain model (if specified)
    if watch_config.get("model"):
        if not re.search(rf"\b{re.escape(watch_config['model'])}\b", title, re.IGNORECASE):
            return False

    # Must contain ALL required_terms
    for term in watch_config.get("required_terms", []):
        if term not in title:
            return False

    return True


# ------------------------------------------------------------
# Search eBay for a single watch
# ------------------------------------------------------------

def search_ebay_for_watch(token, watch_config):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
        "Accept": "application/json",
    }

    results = {}

    for search_term in watch_config.get("search_terms", []):
        params = {
            "q": search_term,
            "limit": 50,
            "sort": "price",
        }

        response = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data.get("itemSummaries", []):
            if not is_valid_listing(item, watch_config):
                continue

            item_id = item.get("itemId")
            if not item_id:
                continue

            price_data = item.get("price", {})
            try:
                price = float(price_data.get("value"))
            except (TypeError, ValueError):
                continue

            shipping = 0.0
            shipping_options = item.get("shippingOptions", [])
            if shipping_options:
                shipping_cost = shipping_options[0].get("shippingCost", {}).get("value")
                try:
                    shipping = float(shipping_cost or 0)
                except (TypeError, ValueError):
                    shipping = 0.0

            total_price = round(price + shipping, 2)

            results[item_id] = {
                "source": "eBay",
                "price": total_price,
                "condition": item.get("condition", "Condition not specified"),
                "title": item.get("title", watch_config["name"]),
                "link": item.get("itemWebUrl", ""),
                "item_id": item_id,
            }

    return list(results.values())


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    # Load watch configuration
    with open("watches.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    token = get_access_token()
    print("Searching eBay...")

    all_watch_data = {}
    for watch in config["watches"]:
        print(f"  Fetching {watch['name']}...")
        listings = search_ebay_for_watch(token, watch)
        all_watch_data[watch["id"]] = {
            "name": watch["name"],
            "msrp": watch.get("msrp"),
            "target_price": watch.get("target_price"),
            "excellent_price": watch.get("excellent_price"),
            "listings": listings,
        }
        print(f"    Found {len(listings)} matching listings.")

    # Save per-watch eBay data
    with open("ebay_data.json", "w", encoding="utf-8") as f:
        json.dump(all_watch_data, f, indent=2)

    print("eBay data saved.")


if __name__ == "__main__":
    main()
