import json
import re
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


def extract_price_from_page(soup):
    """
    Extract the main price from a WatchMaxx product page.
    Tries multiple strategies to find the price.
    """
    # Strategy 1: Check for meta tags with itemprop="price"
    price_meta = soup.find("meta", {"itemprop": "price"})
    if price_meta and price_meta.get("content"):
        try:
            return float(price_meta["content"])
        except (TypeError, ValueError):
            pass

    # Strategy 2: Look for common price class names
    price_selectors = [
        ".price",
        ".current-price",
        ".product-price",
        ".special-price",
        ".now-price",
        ".sale-price"
    ]
    for selector in price_selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            # Find first dollar amount
            match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
            if match:
                try:
                    return float(match.group())
                except (TypeError, ValueError):
                    pass

    # Strategy 3: Look for any prominent dollar amount in the body
    body_text = soup.get_text()
    # Find all dollar amounts like $XXX.XX or $XXX
    matches = re.findall(r"\$\s*([\d,]+\.?\d*)", body_text)
    for match in matches:
        try:
            val = float(match.replace(",", ""))
            # Filter out very small amounts (like $5 shipping) and very large ones (MSRP)
            if 50 < val < 10000:
                return val
        except (TypeError, ValueError):
            pass

    return None


def main():
    # Load watch configuration
    with open("watches.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    all_data = {}

    for watch in config["watches"]:
        url = watch.get("watchmaxx_url")
        if not url:
            continue

        print(f"Checking WatchMaxx for {watch['name']}...")

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            price = extract_price_from_page(soup)

            if price is None:
                print(f"  Could not extract price from {url}")
                all_data[watch["id"]] = {
                    "name": watch["name"],
                    "listings": []
                }
                continue

            # Create a listing entry
            listing = {
                "source": "WatchMaxx",
                "price": round(price, 2),
                "condition": "New (Grey Market)",
                "title": watch["name"],
                "link": url
            }

            all_data[watch["id"]] = {
                "name": watch["name"],
                "listings": [listing]
            }

            print(f"  Found price: ${price:.2f}")

        except Exception as e:
            print(f"  Error fetching WatchMaxx: {e}")
            all_data[watch["id"]] = {
                "name": watch["name"],
                "listings": []
            }

    # Save to watchmaxx_data.json
    with open("watchmaxx_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print("WatchMaxx data saved.")


if __name__ == "__main__":
    main()
