# app/api/predict.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ML Price Predictor (ONNX LightGBM)
from app.services.ml_predictor import predict_price

# Existing Valuation Services
from app.services.combined_model import get_full_property_insights
from app.services.land_valuation import calculate_land_value
from app.services.price_trends import calculate_price_trends


router = APIRouter(prefix="/predict", tags=["Valuation & ML Pricing"])


# ------------------------------------------------
# City-wise rent-to-price ratio
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
# Request Models
# ------------------------------------------------
class ValuationRequest(BaseModel):
    city: str
    state: str
    crime_index: float
    sqft: float


class FullPropertyRequest(BaseModel):
    city: str
    state: str
    sqft: float
    bedrooms: int
    bathrooms: int
    age: float
    crime_index: float
    amenities_count: int
    road_width: float
    zone: str


class LandValuationRequest(BaseModel):
    city: str
    state: str
    sqft: float
    road_width: float
    zone: str


# --------------------------------------------------------
# FULL PROPERTY VALUATION + ML PRICE (ONNX)
# --------------------------------------------------------
@router.post("/property-valuation")
async def property_valuation(request: FullPropertyRequest):
    try:
        city = request.city.lower()
        state = request.state.lower()
        zone = request.zone.lower()

        # 1️⃣ Insights Model
        base_result = await get_full_property_insights(
            city=city,
            state=state,
            crime_index=request.crime_index
        )

        price_per_sqft = base_result["pricing"]["final_price_per_sqft"]
        total_value = round(price_per_sqft * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = total_value

        # 2️⃣ Rent Estimation
        rent_ratio = RENT_RATIO.get(city, RENT_RATIO["default"])
        monthly_rent = (total_value * rent_ratio) / 12

        amenities_score = base_result["pricing"]["amenities_score"]
        crime_effect = base_result["pricing"]["crime_effect_percent"]
        inflation = base_result["pricing"]["inflation_adjustment_percent"]

        monthly_rent *= (1 + amenities_score * 0.10)
        if crime_effect < 0:
            monthly_rent *= (1 - abs(crime_effect) / 100)
        monthly_rent *= (1 + inflation / 200)
        monthly_rent = round(monthly_rent, 2)

        rent_confidence = round(
            base_result["overall_confidence"] * 0.7 + amenities_score * 0.3, 2
        )

        base_result["pricing"]["rent_estimate"] = {
            "monthly_rent": monthly_rent,
            "rent_ratio_used": rent_ratio,
            "rent_confidence": rent_confidence,
        }

        # 3️⃣ Price Trends
        base_result["pricing"]["price_trends"] = calculate_price_trends(
            inflation_rate=inflation,
            amenities_score=amenities_score,
            crime_effect=crime_effect
        )

        # 4️⃣ ML ONNX Model Prediction
        ml_price = predict_price(
            city=city,
            state=state,
            sqft=request.sqft,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            age=request.age,
            crime_index=request.crime_index,
            amenities_count=request.amenities_count,
            road_width=request.road_width,
            zone=zone
        )

        base_result["ml_predicted_price"] = ml_price

        return base_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property valuation failed: {str(e)}")


# --------------------------------------------------------
# BASIC VALUATION ENDPOINT
# --------------------------------------------------------
@router.post("/valuation")
async def valuation(request: ValuationRequest):
    try:
        city = request.city.lower()
        state = request.state.lower()

        base_result = await get_full_property_insights(
            city=city,
            state=state,
            crime_index=request.crime_index
        )

        price_sqft = base_result["pricing"]["final_price_per_sqft"]
        total_value = round(price_sqft * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = total_value

        rent_ratio = RENT_RATIO.get(city, RENT_RATIO["default"])
        monthly_rent = (total_value * rent_ratio) / 12

        amenities_score = base_result["pricing"]["amenities_score"]
        crime_effect = base_result["pricing"]["crime_effect_percent"]
        inflation = base_result["pricing"]["inflation_adjustment_percent"]

        monthly_rent *= (1 + amenities_score * 0.10)
        if crime_effect < 0:
            monthly_rent *= (1 - abs(crime_effect) / 100)
        monthly_rent *= (1 + inflation / 200)

        base_result["pricing"]["rent_estimate"] = {
            "monthly_rent": round(monthly_rent, 2),
            "rent_ratio_used": rent_ratio,
        }

        base_result["pricing"]["price_trends"] = calculate_price_trends(
            inflation_rate=inflation,
            amenities_score=amenities_score,
            crime_effect=crime_effect
        )

        return base_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation processing error: {str(e)}")


# --------------------------------------------------------
# LAND VALUATION
# --------------------------------------------------------
@router.post("/land-valuation")
async def land_valuation(request: LandValuationRequest):
    try:
        return await calculate_land_value(
            city=request.city.lower(),
            state=request.state.lower(),
            sqft=request.sqft,
            road_width=request.road_width,
            zone=request.zone.lower(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Land valuation failed: {str(e)}")
