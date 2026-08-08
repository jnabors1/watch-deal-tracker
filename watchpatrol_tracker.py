import json
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


WATCHPATROL_URL = (
    "https://www.watchpatrol.net/discover/brands/vaer/c5-field/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


def is_exact_target(title):
    """
    Only accept listings that appear to be the
    Vaer C5 Recon Field Solar.

    We intentionally require 'recon' so that
    C5 Tactical / C5 Field / C5 Navy listings
    don't get mixed into the target watch.
    """

    text = title.lower()

    if "vaer" not in text:
        return False

    if not re.search(r"\bc5\b", text):
        return False

    if "recon" not in text:
        return False

    if "solar" not in text:
        return False

    return True


def extract_price(text):
    """
    Find the first dollar price in listing text.
    """

    match = re.search(
        r"\$\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        text
    )

    if not match:
        return None

    return float(
        match.group(1).replace(",", "")
    )


def get_source(text):
    """
    Identify the marketplace/forum when possible.
    """

    lower = text.lower()

    if "reddit" in lower:
        return "Reddit"

    if "watchuseek" in lower:
        return "WatchUSeek"

    if "rolexforums" in lower:
        return "Rolex Forums"

    if "klocksnack" in lower:
        return "Klocksnack"

    return "WatchPatrol"


def fetch_listings():

    response = requests.get(
        WATCHPATROL_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    listings = []
    seen_urls = set()

    # Look through links on the page.
    for link in soup.find_all("a", href=True):

        title = link.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        # We only care about listings containing
        # the exact target model terms.
        if not is_exact_target(title):
            continue

        price = extract_price(title)

        if price is None:
            continue

        url = link["href"]

        if url.startswith("/"):
            url = (
                "https://www.watchpatrol.net"
                + url
            )

        if url in seen_urls:
            continue

        seen_urls.add(url)

        listings.append({
            "source": get_source(title),
            "price": price,
            "condition": "Used / forum listing",
            "title": title,
            "link": url
        })

    return listings


def save_data(listings):

    listings.sort(
        key=lambda item: item["price"]
    )

    output = {
        "source": "WatchPatrol",
        "target": "Vaer C5 Recon Field Solar 40mm",
        "updated": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC"),
        "listings": listings
    }

    with open(
        "watchpatrol.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2
        )

    print(
        f"Found {len(listings)} exact-target listings."
    )


def main():

    print("Checking WatchPatrol...")

    listings = fetch_listings()

    save_data(listings)

    for listing in listings:

        print(
            f"${listing['price']:.2f} "
            f"- {listing['source']} - "
            f"{listing['title']}"
        )


if __name__ == "__main__":
    main()
