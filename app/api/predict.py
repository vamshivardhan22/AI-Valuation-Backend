# app/api/predict.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.combined_model import get_full_property_insights
from app.services.land_valuation import calculate_land_value
from app.services.price_trends import calculate_price_trends     # <-- Task 4 Added


router = APIRouter(prefix="/predict", tags=["Valuation"])


# ------------------------------------------------
# City-wise rent-to-price ratio (Used in rent model)
# ------------------------------------------------
RENT_RATIO = {
    "hyderabad": 0.025,
    "bangalore": 0.028,
    "bengaluru": 0.028,
    "chennai": 0.030,
    "pune": 0.032,
    "mumbai": 0.019,
    "delhi": 0.020,
    "faridabad": 0.023,
    "kolkata": 0.022,
    "jaipur": 0.024,
    "default": 0.025
}


# ------------------------------------------------
# Request Body Models
# ------------------------------------------------

class ValuationRequest(BaseModel):
    city: str
    state: str
    crime_index: float
    sqft: float


class LandValuationRequest(BaseModel):
    city: str
    state: str
    sqft: float
    road_width: float
    zone: str



# ------------------------------------------------
# MAIN PROPERTY VALUATION ENDPOINT  
# (Task 1 + Task 2 + Task 4)
# ------------------------------------------------
@router.post("/valuation")
async def valuation(request: ValuationRequest):
    try:
        # Step 1: AI valuation per sqft + insights
        base_result = await get_full_property_insights(
            city=request.city,
            state=request.state,
            crime_index=request.crime_index
        )

        # ----------------------------
        # FULL PROPERTY VALUE
        # ----------------------------
        price_per_sqft = base_result["pricing"]["final_price_per_sqft"]
        total_value = round(price_per_sqft * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = total_value

        # ----------------------------
        # RENT PREDICTION (Task 2)
        # ----------------------------
        city_lower = request.city.lower()
        rent_ratio = RENT_RATIO.get(city_lower, RENT_RATIO["default"])

        yearly_rent = total_value * rent_ratio
        monthly_rent = yearly_rent / 12

        amenities_score = base_result["pricing"]["amenities_score"]
        crime_effect = base_result["pricing"]["crime_effect_percent"]
        inflation = base_result["pricing"]["inflation_adjustment_percent"]

        # + Amenities increase rent
        monthly_rent *= (1 + amenities_score * 0.10)

        # - Crime reduces rent
        if crime_effect < 0:
            monthly_rent *= (1 - abs(crime_effect) / 100)

        # Inflation adjustment
        monthly_rent *= (1 + inflation / 200)

        monthly_rent = round(monthly_rent, 2)

        rent_confidence = round(
            (base_result["overall_confidence"] * 0.7) +
            (amenities_score * 0.3), 2
        )

        base_result["pricing"]["rent_estimate"] = {
            "monthly_rent": monthly_rent,
            "rent_ratio_used": rent_ratio,
            "rent_confidence": rent_confidence
        }

        # ----------------------------
        # PRICE TRENDS (Task 4)
        # ----------------------------
        trends = calculate_price_trends(
            inflation_rate=inflation,
            amenities_score=amenities_score,
            crime_effect=crime_effect
        )

        base_result["pricing"]["price_trends"] = trends

        return base_result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Valuation processing error: {str(e)}"
        )



# ------------------------------------------------
# LAND VALUATION ENDPOINT (Task 3)
# ------------------------------------------------
@router.post("/land-valuation")
async def land_valuation(request: LandValuationRequest):
    try:
        result = await calculate_land_value(
            city=request.city,
            state=request.state,
            sqft=request.sqft,
            road_width=request.road_width,
            zone=request.zone
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Land valuation failed: {str(e)}"
        )
