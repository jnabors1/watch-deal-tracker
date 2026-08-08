import json
from datetime import datetime, timezone


def load_json(filename):
    """Safely load a JSON file, return None if missing or invalid."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    # Load both sources
    wp_data = load_json("watchpatrol.json")
    ebay_data = load_json("ebay_data.json")

    all_listings = []
    sources_used = []

    if wp_data and "listings" in wp_data:
        all_listings.extend(wp_data["listings"])
        sources_used.append("WatchPatrol")
        print(f"WatchPatrol: {len(wp_data['listings'])} listings")

    if ebay_data and "listings" in ebay_data:
        all_listings.extend(ebay_data["listings"])
        sources_used.append("eBay")
        print(f"eBay: {len(ebay_data['listings'])} listings")

    # Sort by price (lowest first)
    all_listings.sort(key=lambda x: x.get("price", float("inf")))

    # Calculate dashboard stats
    if all_listings:
        best = all_listings[0]
        prices = [l["price"] for l in all_listings]
        best_price = best["price"]
        lowest_price = min(prices)
        typical_price = round(sum(prices) / len(prices), 2)
        best_source = best.get("source", "Unknown")
        best_link = best.get("link", "#")
    else:
        best_price = 0
        lowest_price = 0
        typical_price = 0
        best_source = "No listings found"
        best_link = "#"

    output = {
        "best_price": best_price,
        "best_source": best_source,
        "best_link": best_link,
        "lowest_price": lowest_price,
        "typical_price": typical_price,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "listings": all_listings,
        "sources": sources_used,  # Tells the dashboard which sources are active
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Merged {len(all_listings)} total listings from {', '.join(sources_used) or 'none'}.")


if __name__ == "__main__":
    main()
