import json
from datetime import datetime, timezone, timedelta
import statistics


def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_history():
    try:
        with open("history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history(history):
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def compute_median(prices):
    if not prices:
        return 0
    return round(statistics.median(prices), 2)


def main():
    # Load watch configuration
    with open("watches.json", "r", encoding="utf-8") as f:
        watch_configs = {w["id"]: w for w in json.load(f)["watches"]}

    ebay_data = load_json("ebay_data.json") or {}
    wp_data = load_json("watchpatrol.json") or {}
    watchmaxx_data = load_json("watchmaxx_data.json") or {}

    history = load_history()

    merged_data = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for watch_id, watch_meta in watch_configs.items():
        all_listings = []

        if watch_id in ebay_data:
            all_listings.extend(ebay_data[watch_id].get("listings", []))

        if wp_data and "watches" in wp_data and watch_id in wp_data["watches"]:
            all_listings.extend(wp_data["watches"][watch_id].get("listings", []))

        if watch_id in watchmaxx_data:
            all_listings.extend(watchmaxx_data[watch_id].get("listings", []))

        all_listings.sort(key=lambda x: x.get("price", float("inf")))

        if all_listings:
            prices = [l["price"] for l in all_listings]
            best = all_listings[0]
            best_price = best["price"]
            lowest_price = min(prices)
            median_price = compute_median(prices)
            best_source = best.get("source", "Unknown")
            best_link = best.get("link", "#")
            count = len(all_listings)
        else:
            best_price = 0
            lowest_price = 0
            median_price = 0
            best_source = "No listings found"
            best_link = "#"
            count = 0

        # --- Price History Update ---
        if watch_id not in history:
            history[watch_id] = []

        history[watch_id].append({
            "date": today,
            "best": best_price,
            "lowest": lowest_price,
            "median": median_price,
            "count": count
        })

        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        history[watch_id] = [
            entry for entry in history[watch_id]
            if entry["date"] >= cutoff_str
        ]

        all_time_low = None
        thirty_day_low = None
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        for entry in history[watch_id]:
            if entry["best"] > 0:
                if all_time_low is None or entry["best"] < all_time_low:
                    all_time_low = entry["best"]
                if entry["date"] >= thirty_days_ago:
                    if thirty_day_low is None or entry["best"] < thirty_day_low:
                        thirty_day_low = entry["best"]

        if all_time_low is None:
            all_time_low = 0
        if thirty_day_low is None:
            thirty_day_low = 0

        official_price = watch_meta.get("msrp", 0)
        official_url = watch_meta.get("msrp_url", "#")

        merged_data[watch_id] = {
            "name": watch_meta["name"],
            "brand": watch_meta.get("brand", ""),  # <-- ADDED
            "display_size": watch_meta.get("display_size", ""),
            "display_movement": watch_meta.get("display_movement", ""),
            "official_price": official_price,
            "official_url": official_url,
            "image_url": watch_meta.get("image_url", ""),
            "target_price": watch_meta.get("target_price"),
            "excellent_price": watch_meta.get("excellent_price"),
            "best_price": best_price,
            "best_source": best_source,
            "best_link": best_link,
            "lowest_price": lowest_price,
            "median_price": median_price,
            "listings": all_listings,
            "all_time_low": all_time_low,
            "thirty_day_low": thirty_day_low,
            "sources": [],
            "exact_filter_terms": watch_meta.get("exact_filter_terms", [])
        }

        sources = []
        if watch_id in ebay_data and ebay_data[watch_id].get("listings"):
            sources.append("eBay")
        if wp_data and "watches" in wp_data and watch_id in wp_data["watches"] and wp_data["watches"][watch_id].get("listings"):
            sources.append("WatchPatrol")
        if watch_id in watchmaxx_data and watchmaxx_data[watch_id].get("listings"):
            sources.append("WatchMaxx")
        merged_data[watch_id]["sources"] = sources

    save_history(history)

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
