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

# Set to True to require "Recon" in the title (tighter filtering)
STRICT_MODE = False   # Change to True later if you want to restrict to Recon only

# Broader searches to catch more listings
SEARCHES = [
    '"Vaer C5"',
    '"Vaer C5 Recon"',
    '"Vaer C5 Field"',
    '"Vaer C5 Solar"',
    '"Vaer C5 Recon Solar"',
    '"C5 Recon"',
]

# We don't want accessories, straps, parts, etc.
EXCLUDE_TERMS = [
    "strap",
    "band",
    "bracelet",
    "replacement",
    "parts",
    "crystal",
    "spring bar",
    "buckle",
    "manual",
    "box only",
    "case only",
]


# ------------------------------------------------------------
# Get eBay application access token
# ------------------------------------------------------------

def get_access_token():

    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"

    encoded = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded}",
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    response = requests.post(
        TOKEN_URL,
        headers=headers,
        data=data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["access_token"]


# ------------------------------------------------------------
# Determine whether a listing looks like our watch
# ------------------------------------------------------------

def is_valid_listing(item):

    title = item.get("title", "").lower()

    # Exclude obvious accessories and unrelated items.
    for term in EXCLUDE_TERMS:
        if term in title:
            return False

    # Must contain Vaer.
    if "vaer" not in title:
        return False

    # Must contain C5.
    if not re.search(r"\bc5\b", title):
        return False

    # If STRICT_MODE is True, require "Recon"
    if STRICT_MODE:
        if "recon" not in title:
            return False

    # Otherwise, require at least one of "recon", "field", "solar"
    valid_model_terms = ["recon", "field", "solar"]
    if not any(term in title for term in valid_model_terms):
        return False

    return True


# ------------------------------------------------------------
# Search eBay
# ------------------------------------------------------------

def search_ebay(token):

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
        "Accept": "application/json",
    }

    results = {}

    for search_term in SEARCHES:

        params = {
            "q": search_term,
            "limit": 50,
            "sort": "price",
        }

        response = requests.get(
            SEARCH_URL,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        for item in data.get("itemSummaries", []):

            if not is_valid_listing(item):
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

            shipping_options = item.get(
                "shippingOptions",
                []
            )

            if shipping_options:

                shipping_cost = (
                    shipping_options[0]
                    .get("shippingCost", {})
                    .get("value")
                )

                try:
                    shipping = float(shipping_cost or 0)
                except (TypeError, ValueError):
                    shipping = 0.0

            total_price = round(
                price + shipping,
                2
            )

            results[item_id] = {
                "source": "eBay",
                "price": total_price,
                "condition": item.get(
                    "condition",
                    "Condition not specified"
                ),
                "title": item.get(
                    "title",
                    "Vaer C5 Recon Field Solar"
                ),
                "link": item.get(
                    "itemWebUrl",
                    ""
                ),
                "item_id": item_id,
            }

    return list(results.values())


# ------------------------------------------------------------
# Create dashboard data
# ------------------------------------------------------------

def update_dashboard(listings):

    listings.sort(
        key=lambda x: x["price"]
    )

    if listings:

        best = listings[0]

        prices = [
            x["price"]
            for x in listings
        ]

        average = sum(prices) / len(prices)

        best_price = best["price"]
        lowest_price = min(prices)
        typical_price = round(average, 2)

        best_source = (
            f"eBay — {best['condition']}"
        )

        best_link = best["link"]

    else:

        best_price = 0
        lowest_price = 0
        typical_price = 0
        best_source = "No matching listings found"
        best_link = "#"

    output = {
        "best_price": best_price,
        "best_source": best_source,
        "best_link": best_link,
        "lowest_price": lowest_price,
        "typical_price": typical_price,
        "updated": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC"),
        "listings": listings,
    }

    with open(
        "ebay_data.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2
        )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    print("Getting eBay access token...")

    token = get_access_token()

    print("Searching eBay...")

    listings = search_ebay(token)

    print(
        f"Found {len(listings)} matching listings."
    )

    update_dashboard(listings)

    print("Dashboard data updated.")


if __name__ == "__main__":
    main()
