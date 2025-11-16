# app/services/combined_model.py

import asyncio

from app.services.city_price import get_city_price
from app.services.state_price import get_state_price
from app.services.crime import get_crime_impact
from app.services.inflation import get_inflation_adjustment
from app.services.amenities import get_amenities
from app.services.geocode import get_coordinates
from app.services.sales import get_recent_sales


def calculate_final_price(city_data, state_data, crime_effect, inflation_adj, amenities_score):
    """
    Combine all factors into an adjusted final price per sqft.
    """
    base_city = city_data.get("avg_price_sqft", 0)
    base_state = state_data.get("state_avg_price_sqft", 0)

    # Weighted base price
    base_price = (0.65 * base_city) + (0.35 * base_state)

    # Multipliers
    crime_multiplier = 1 + (crime_effect / 100)
    inflation_multiplier = 1 + (inflation_adj / 100)
    amenities_multiplier = 1 + (amenities_score * 0.15)

    final_price = base_price * crime_multiplier * inflation_multiplier * amenities_multiplier
    return round(final_price, 2)


async def get_full_property_insights(city: str, state: str, crime_index: float):
    """
    Full async pipeline combining all valuation components.
    """

    # STEP 1: City price
    city_info = await get_city_price(city)
    if city_info is None:
        city_info = {"error": "City data not found", "confidence": 0}

    # STEP 2: State price
    state_info = get_state_price(state)
    if "error" in state_info:
        state_info["confidence"] = 0

    # STEP 3: Crime effect
    crime_effect = get_crime_impact(crime_index)

    # STEP 4: Inflation
    inflation_adjustment = get_inflation_adjustment()

    # STEP 5: Geocode
    coords = await get_coordinates(city)
    if coords:
        lat = float(coords["latitude"])
        lon = float(coords["longitude"])
    else:
        lat = lon = None

    # STEP 6: Amenities (NEW BREAKDOWN MODEL)
    if lat is not None and lon is not None:
        amenities_raw = await get_amenities(lat, lon)

        amenities_score = amenities_raw["score"]
        amenities_breakdown = amenities_raw["counts"]
        amenities_total = amenities_raw["total"]
    else:
        amenities_score = 0
        amenities_breakdown = {}
        amenities_total = 0

    # STEP 7: Sales data
    if lat is not None and lon is not None:
        sales_list = await get_recent_sales(lat, lon)
        sales_confidence = min(len(sales_list) / 30, 1.0)
    else:
        sales_list = []
        sales_confidence = 0

    # STEP 8: Final price calculation
    final_price = calculate_final_price(
        city_info,
        state_info,
        crime_effect,
        inflation_adjustment,
        amenities_score
    )

    # STEP 9: Final confidence score
    confidence = round(
        (city_info.get("confidence", 0) +
         state_info.get("confidence", 0) +
         sales_confidence) / 3,
        2
    )

    # FINAL OUTPUT STRUCTURE
    return {
        "location": {
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon
        },
        "pricing": {
            "city_insights": city_info,
            "state_insights": state_info,
            "crime_effect_percent": crime_effect,
            "inflation_adjustment_percent": inflation_adjustment,

            # NEW AMENITY DATA
            "amenities_score": round(amenities_score, 2),
            "amenities_breakdown": {
                "details": amenities_breakdown,
                "total_amenities": amenities_total,
                "amenities_influence_percent": round(amenities_score * 10, 2)
            },

            "recent_sales_count": len(sales_list),
            "final_price_per_sqft": final_price
        },
        "overall_confidence": confidence
    }


# Manual test
if __name__ == "__main__":
    async def test():
        result = await get_full_property_insights(
            city="Faridabad",
            state="Haryana",
            crime_index=43.4
        )
        print(result)

    asyncio.run(test())
