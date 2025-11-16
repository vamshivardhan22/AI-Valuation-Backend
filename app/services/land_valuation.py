# app/services/land_valuation.py

from app.services.city_price import get_city_price
from app.services.inflation import get_inflation_adjustment
from app.services.crime import get_crime_impact

# -----------------------------
#  STATIC CIRCLE RATES (OPTION A)
# -----------------------------
CIRCLE_RATES = {
    "hyderabad": 6000,
    "faridabad": 3500,
    "bangalore": 7000,
    "mumbai": 9000,
    "chennai": 5000,
    "pune": 4500,
    "delhi": 8000
}


# -----------------------------------
# LAND VALUATION ENGINE (A + B Hybrid)
# -----------------------------------
async def calculate_land_value(city: str, state: str, sqft: float, road_width: float, zone: str):

    zone = zone.lower()
    city_lower = city.lower()

    # 1️⃣ Try STATIC circle rate first (A)
    circle_rate = CIRCLE_RATES.get(city_lower)

    # 2️⃣ Fetch city price for dynamic fallback (B)
    city_info = await get_city_price(city)

    if city_info:
        dynamic_rate = city_info["avg_price_sqft"] * 0.45
    else:
        dynamic_rate = None

    # Base rate (A + B hybrid)
    if circle_rate:
        base_rate = (circle_rate + (dynamic_rate or circle_rate)) / 2
    else:
        base_rate = dynamic_rate

    # If both missing
    if base_rate is None:
        return {
            "error": "City price and circle rate unavailable"
        }

    # 3️⃣ Zone multiplier
    ZONE_MULTIPLIER = {
        "residential": 1.0,
        "commercial": 1.25,
        "industrial": 0.85,
        "agricultural": 0.65
    }

    zone_factor = ZONE_MULTIPLIER.get(zone, 1.0)

    # 4️⃣ Road width factor
    if road_width >= 40:
        road_factor = 1.15
    elif road_width >= 30:
        road_factor = 1.10
    elif road_width >= 20:
        road_factor = 1.05
    else:
        road_factor = 1.00

    # 5️⃣ Market adjustment (inflation)
    inflation_adj = get_inflation_adjustment() / 100

    # 6️⃣ Final land rate per sqft
    final_rate = base_rate * zone_factor * road_factor * (1 + inflation_adj)
    final_rate = round(final_rate, 2)

    # 7️⃣ Total land value
    total_value = round(final_rate * sqft, 2)

    return {
        "inputs": {
            "city": city,
            "state": state,
            "sqft": sqft,
            "road_width": road_width,
            "zone": zone
        },
        "base_value": {
            "circle_rate": circle_rate,
            "dynamic_rate": dynamic_rate,
            "final_base_rate": round(base_rate, 2)
        },
        "adjustments": {
            "zone_multiplier": zone_factor,
            "road_width_factor": road_factor,
            "inflation_adjustment": inflation_adj
        },
        "final_output": {
            "rate_per_sqft": final_rate,
            "total_land_value": total_value
        }
    }
