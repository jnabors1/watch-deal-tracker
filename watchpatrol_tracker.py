import json
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


def is_exact_target(title, watch_config):
    """
    Check if listing title matches the watch's required terms.
    Model (reference number) is optional – helps but doesn't block.
    """
    title_lower = title.lower()

    # Exclude terms
    for term in watch_config.get("exclude_terms", []):
        if term in title_lower:
            return False

    # Must contain brand
    if watch_config.get("brand", "").lower() not in title_lower:
        return False

    # Must contain all required_terms
    for term in watch_config.get("required_terms", []):
        if term not in title_lower:
            return False

    # Model (reference number) is optional – if it exists, it helps,
    # but we don't reject listings without it.
    # Many sellers don't include the reference number in the title.
    # We'll still check it if present, but it won't block the listing.

    return True


def extract_price(text):
    match = re.search(r"\$\s*([0-9,]+(?:\.[0-9]{1,2})?)", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def get_source(text):
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


def fetch_listings_for_watch(watch_config):
    url = watch_config.get("watchpatrol_url")
    if not url:
        return []

    print(f"  Fetching from: {url}")

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    listings = []
    seen_urls = set()

    # DEBUG: Print all titles found
    print("  DEBUG: All titles found on the page:")

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)
        if not title:
            continue

        # Print every title for debugging
        print(f"    - {title}")

        if not is_exact_target(title, watch_config):
            continue

        price = extract_price(title)
        if price is None:
            continue

        url_href = link["href"]
        if url_href.startswith("/"):
            url_href = "https://www.watchpatrol.net" + url_href

        if url_href in seen_urls:
            continue
        seen_urls.add(url_href)

        listings.append({
            "source": get_source(title),
            "price": price,
            "condition": "Used / forum listing",
            "title": title,
            "link": url_href
        })

    return listings


def main():
    # Load watch configuration
    with open("watches.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    all_watch_data = {}

    for watch in config["watches"]:
        print(f"Checking WatchPatrol for {watch['name']}...")
        listings = fetch_listings_for_watch(watch)
        all_watch_data[watch["id"]] = {
            "name": watch["name"],
            "listings": listings,
        }
        print(f"  Found {len(listings)} exact-target listings.")

    # Save per-watch WatchPatrol data
    output = {
        "source": "WatchPatrol",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "watches": all_watch_data,
    }

    with open("watchpatrol.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("WatchPatrol data saved.")


if __name__ == "__main__":
    main()
