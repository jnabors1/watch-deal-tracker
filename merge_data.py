import json
from datetime import datetime, timezone


def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    # Load watch configuration to get metadata (MSRP, targets)
    with open("watches.json", "r", encoding="utf-8") as f:
        watch_configs = {w["id"]: w for w in json.load(f)["watches"]}

    ebay_data = load_json("ebay_data.json") or {}
    wp_data = load_json("watchpatrol.json") or {}

    merged_data = {}

    for watch_id, watch_meta in watch_configs.items():
        # Gather listings from both sources
        all_listings = []

        # eBay
        if watch_id in ebay_data:
            all_listings.extend(ebay_data[watch_id].get("listings", []))

        # WatchPatrol (nested under "watches" key)
        if wp_data and "watches" in wp_data and watch_id in wp_data["watches"]:
            all_listings.extend(wp_data["watches"][watch_id].get("listings", []))

        # Sort by price
        all_listings.sort(key=lambda x: x.get("price", float("inf")))

        # Calculate stats
        if all_listings:
            prices = [l["price"] for l in all_listings]
            best = all_listings[0]
            best_price = best["price"]
            lowest_price = min(prices)
            typical_price = round(sum(prices) / len(prices), 2)
            best_source = best.get("source", "Unknown")
            best_link = best.get("link", "#")
            best_condition = best.get("condition", "")
        else:
            best_price = 0
            lowest_price = 0
            typical_price = 0
            best_source = "No listings found"
            best_link = "#"
            best_condition = ""

        merged_data[watch_id] = {
            "name": watch_meta["name"],
            "msrp": watch_meta.get("msrp"),
            "target_price": watch_meta.get("target_price"),
            "excellent_price": watch_meta.get("excellent_price"),
            "best_price": best_price,
            "best_source": best_source,
            "best_link": best_link,
            "lowest_price": lowest_price,
            "typical_price": typical_price,
            "listings": all_listings,
            "sources": []  # can add source names if needed
        }

        # Add source tracking
        sources = []
        if watch_id in ebay_data and ebay_data[watch_id].get("listings"):
            sources.append("eBay")
        if wp_data and "watches" in wp_data and watch_id in wp_data["watches"] and wp_data["watches"][watch_id].get("listings"):
            sources.append("WatchPatrol")
        merged_data[watch_id]["sources"] = sources

    # Final output
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "watches": merged_data,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    total_listings = sum(len(w["listings"]) for w in merged_data.values())
    print(f"Merged data for {len(merged_data)} watch(es), total listings: {total_listings}")


if __name__ == "__main__":
    main()
