import json
from datetime import datetime, timezone, timedelta
import os


def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_history():
    """Load existing history, or return empty dict."""
    try:
        with open("history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history(history):
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def main():
    # Load watch configuration
    with open("watches.json", "r", encoding="utf-8") as f:
        watch_configs = {w["id"]: w for w in json.load(f)["watches"]}

    ebay_data = load_json("ebay_data.json") or {}
    wp_data = load_json("watchpatrol.json") or {}

    # Load existing history
    history = load_history()

    merged_data = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
            count = len(all_listings)
        else:
            best_price = 0
            lowest_price = 0
            typical_price = 0
            best_source = "No listings found"
            best_link = "#"
            best_condition = ""
            count = 0

        # --- Price History Update ---
        if watch_id not in history:
            history[watch_id] = []

        # Append today's snapshot
        history[watch_id].append({
            "date": today,
            "best": best_price,
            "lowest": lowest_price,
            "typical": typical_price,
            "count": count
        })

        # Keep only the last 365 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        history[watch_id] = [
            entry for entry in history[watch_id]
            if entry["date"] >= cutoff_str
        ]

        # Calculate historical stats from history
        all_time_low = None
        thirty_day_low = None
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        for entry in history[watch_id]:
            # Check if entry has a valid price (best > 0 means we had listings)
            if entry["best"] > 0:
                if all_time_low is None or entry["best"] < all_time_low:
                    all_time_low = entry["best"]
                if entry["date"] >= thirty_days_ago:
                    if thirty_day_low is None or entry["best"] < thirty_day_low:
                        thirty_day_low = entry["best"]

        # If no history with prices, set to 0
        if all_time_low is None:
            all_time_low = 0
        if thirty_day_low is None:
            thirty_day_low = 0

        # Prepare final data for this watch
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
            "sources": [],  # Will be filled below
            # --- New history fields ---
            "all_time_low": all_time_low,
            "thirty_day_low": thirty_day_low
        }

        # Add source tracking
        sources = []
        if watch_id in ebay_data and ebay_data[watch_id].get("listings"):
            sources.append("eBay")
        if wp_data and "watches" in wp_data and watch_id in wp_data["watches"] and wp_data["watches"][watch_id].get("listings"):
            sources.append("WatchPatrol")
        merged_data[watch_id]["sources"] = sources

    # Save history back to file
    save_history(history)

    # Final output for data.json
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "watches": merged_data,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    total_listings = sum(len(w["listings"]) for w in merged_data.values())
    print(f"Merged data for {len(merged_data)} watch(es), total listings: {total_listings}")
    print(f"History updated for {len(history)} watch(es).")


if __name__ == "__main__":
    main()
