# app/services/state_price.py

import statistics

def get_state_price(state: str):
    """
    Returns average, min, max price per sqft for a given state.
    Uses offline dummy data (to be replaced with API/database later).
    """

    # --- OFFLINE SAMPLE DATA ---
    # You can later move this into /utils/data/ folder as JSON.
    state_data = {
        "Haryana": [4200, 5000, 4700, 3100, 9200, 6500],
        "Telangana": [3800, 4100, 4500, 5200, 6000],
        "Tamil Nadu": [3200, 3600, 2800, 4100, 5400],
        "Maharashtra": [6100, 7200, 5300, 6800, 8900, 7500],
        "Karnataka": [4300, 4800, 5100, 5900, 6200],
    }

    if state not in state_data:
        return {
            "state": state,
            "error": "State data not available"
        }

    prices = state_data[state]

    avg_price = round(sum(prices) / len(prices), 2)
    min_price = min(prices)
    max_price = max(prices)
    city_count = len(prices)  # you can modify later
    confidence = round(0.75 + (city_count / 100), 2)

    return {
        "state": state,
        "state_avg_price_sqft": avg_price,
        "state_min_price_sqft": min_price,
        "state_max_price_sqft": max_price,
        "city_count": city_count,
        "confidence": confidence
    }


# For quick testing (optional):
if __name__ == "__main__":
    print(get_state_price("Haryana"))
