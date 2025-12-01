# app/api/predict.py

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# JWT Auth (still used for the advanced endpoints)
from app.utils.auth_utils import decode_jwt

# ML price predictor (ONNX LightGBM)
from app.services.ml_predictor import predict_price

# Existing services
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
    "bengengaluru": 0.028,
    "chennai": 0.030,
    "pune": 0.032,
    "mumbai": 0.019,
    "delhi": 0.020,
    "faridabad": 0.023,
    "kolkata": 0.022,
    "jaipur": 0.024,
    "default": 0.025,
}

# ============================================================
# EXISTING REQUEST MODELS (KEEPING AS THEY ARE)
# ============================================================


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


# ============================================================
# 🔥 NEW: SIMPLE MODELS THAT MATCH YOUR FRONTEND FORMS
# ============================================================


class HousePriceRequest(BaseModel):
    area: float
    bedrooms: int
    bathrooms: int
    property_type: str
    bhk: str
    furnishing: str
    build_year: Optional[int] = None
    city: str
    locality: str
    amenities: List[str] = []
    lat: float
    lng: float


class HouseRentRequest(BaseModel):
    area: float
    bedrooms: int
    bathrooms: int
    furnishing: str
    property_type: str
    city: str
    locality: str
    floor: Optional[int] = None
    parking: str
    amenities: List[str] = []
    lat: float
    lng: float


class LandPriceRequest(BaseModel):
    area: float
    city: str
    locality: str
    zone_type: str
    road_width: Optional[float] = None
    corner_plot: bool
    lat: float
    lng: float


# ============================================================
# 1) NEW PUBLIC ENDPOINT – /predict/house-price
# ============================================================


@router.post("/house-price")
async def house_price_endpoint(request: HousePriceRequest):
    """
    Lightweight endpoint used by the House Price UI.
    No auth, just returns a price + range + insights.
    """
    city = request.city.lower().strip()
    state = "telangana"  # fallback – adjust later if you want
    zone = "residential"
    amenities_count = len(request.amenities)

    current_year = datetime.utcnow().year
    if request.build_year and 1800 < request.build_year <= current_year:
        age = max(0, current_year - request.build_year)
    else:
        age = 10.0  # default age if unknown

    # Simple defaults when you don't have crime index / road width yet
    crime_index = 50.0
    road_width = 30.0

    try:
        # Try your actual ML model first
        ml_price = predict_price(
            city=city,
            state=state,
            sqft=request.area,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            age=age,
            crime_index=crime_index,
            amenities_count=amenities_count,
            road_width=road_width,
            zone=zone,
        )

        base_price = float(ml_price)
        confidence = 0.82

    except Exception as e:
        # Fallback: simple heuristic so it NEVER breaks in demo
        base_price = float(request.area) * 6000.0
        confidence = 0.55
        # You still see why ML failed in insights
        fallback_reason = f"(Fallback heuristic used because ML model failed: {e})"
    else:
        fallback_reason = ""

    min_price = base_price * 0.9
    max_price = base_price * 1.1

    insights = (
        f"Estimated price for {request.bhk} {request.property_type} in "
        f"{request.locality}, {request.city}. "
        f"Area={request.area} sqft, amenities={amenities_count}. {fallback_reason}"
    )

    return {
        "predicted_price": round(base_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "confidence": confidence,
        "insights": insights,
    }


# ============================================================
# 2) NEW PUBLIC ENDPOINT – /predict/house-rent
# ============================================================


@router.post("/house-rent")
async def house_rent_endpoint(request: HouseRentRequest):
    """
    Endpoint for the House Rent page.
    Uses price estimate + city-wise rent ratio.
    """
    city = request.city.lower().strip()
    state = "telangana"
    zone = "residential"
    amenities_count = len(request.amenities)

    age = 8.0
    crime_index = 50.0
    road_width = 30.0

    # Step 1: price estimate (reuse the ML model if possible)
    try:
        ml_price = predict_price(
            city=city,
            state=state,
            sqft=request.area,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            age=age,
            crime_index=crime_index,
            amenities_count=amenities_count,
            road_width=road_width,
            zone=zone,
        )
        property_value = float(ml_price)
    except Exception:
        property_value = float(request.area) * 5000.0

    # Step 2: rent from value
    rent_ratio = RENT_RATIO.get(city, RENT_RATIO["default"])
    monthly_rent = (property_value * rent_ratio) / 12

    # Slight tweak based on furnishing/parking
    if request.furnishing.lower().startswith("semi"):
        monthly_rent *= 1.05
    elif request.furnishing.lower().startswith("full"):
        monthly_rent *= 1.10

    if request.parking.lower() == "yes":
        monthly_rent *= 1.03

    min_rent = monthly_rent * 0.9
    max_rent = monthly_rent * 1.1

    insights = (
        f"Estimated rent for {request.property_type} in {request.locality}, {request.city}. "
        f"Area={request.area} sqft, floor={request.floor or 'NA'}, "
        f"furnishing={request.furnishing}, amenities={amenities_count}."
    )

    return {
        "predicted_rent": round(monthly_rent, 2),
        "min_rent": round(min_rent, 2),
        "max_rent": round(max_rent, 2),
        "confidence": 0.78,
        "insights": insights,
    }


# ============================================================
# 3) NEW PUBLIC ENDPOINT – /predict/land-price
# ============================================================


@router.post("/land-price")
async def land_price_endpoint(request: LandPriceRequest):
    """
    Endpoint for Land Price page.
    Tries your land_valuation service first, then falls back.
    """
    city = request.city.lower().strip()
    state = "telangana"
    zone = request.zone_type.lower()

    try:
        # Try existing land valuation service
        service_result = await calculate_land_value(
            city=city,
            state=state,
            sqft=request.area,
            road_width=request.road_width or 30.0,
            zone=zone,
        )

        base_price = float(service_result.get("estimated_land_value", 0.0))
        confidence = float(service_result.get("confidence", 0.8))

    except Exception as e:
        # Fallback: simple heuristic
        base_price = float(request.area) * 3000.0
        confidence = 0.6
        fallback_reason = f"(Fallback heuristic used because land model failed: {e})"
    else:
        fallback_reason = ""

    min_price = base_price * 0.9
    max_price = base_price * 1.1

    insights = (
        f"Estimated value for {request.zone_type} plot in "
        f"{request.locality}, {request.city}. Road width={request.road_width or 'NA'} ft. "
        f"Corner plot={request.corner_plot}. {fallback_reason}"
    )

    return {
        "predicted_price": round(base_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "confidence": confidence,
        "insights": insights,
    }


# ============================================================
# EXISTING ADVANCED ENDPOINTS (JWT-PROTECTED)
# ============================================================


@router.post("/property-valuation")
async def property_valuation(
    request: FullPropertyRequest,
    user=Depends(decode_jwt),  # 🔒 still protected
):
    try:
        req_city = request.city.lower()
        req_state = request.state.lower()
        req_zone = request.zone.lower()

        # 1️⃣ Insights model
        base_result = await get_full_property_insights(
            city=req_city,
            state=req_state,
            crime_index=request.crime_index,
        )

        price_sqft = base_result["pricing"]["final_price_per_sqft"]
        final_value = round(price_sqft * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = final_value

        # 2️⃣ Rent estimation
        rent_ratio = RENT_RATIO.get(req_city, RENT_RATIO["default"])
        monthly_rent = (final_value * rent_ratio) / 12

        amenities = base_result["pricing"]["amenities_score"]
        crime_effect = base_result["pricing"]["crime_effect_percent"]
        inflation = base_result["pricing"]["inflation_adjustment_percent"]

        monthly_rent *= 1 + amenities * 0.10
        if crime_effect < 0:
            monthly_rent *= 1 - abs(crime_effect) / 100
        monthly_rent *= 1 + inflation / 200
        monthly_rent = round(monthly_rent, 2)

        base_result["pricing"]["rent_estimate"] = {
            "monthly_rent": monthly_rent,
            "rent_ratio_used": rent_ratio,
            "rent_confidence": round(
                (base_result["overall_confidence"] * 0.7) + (amenities * 0.3), 2
            ),
        }

        # 3️⃣ Price trends
        base_result["pricing"]["price_trends"] = calculate_price_trends(
            inflation_rate=inflation,
            amenities_score=amenities,
            crime_effect=crime_effect,
        )

        # 4️⃣ ML Price prediction (ONNX)
        ml_price = predict_price(
            city=req_city,
            state=req_state,
            sqft=request.sqft,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            age=request.age,
            crime_index=request.crime_index,
            amenities_count=request.amenities_count,
            road_width=request.road_width,
            zone=req_zone,
        )

        base_result["ml_predicted_price"] = ml_price

        return base_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property valuation failed: {str(e)}")


@router.post("/valuation")
async def valuation(
    request: ValuationRequest,
    user=Depends(decode_jwt),  # 🔒 still protected
):
    try:
        req_city = request.city.lower()
        req_state = request.state.lower()

        base_result = await get_full_property_insights(
            city=req_city,
            state=req_state,
            crime_index=request.crime_index,
        )

        price = base_result["pricing"]["final_price_per_sqft"]
        total_value = round(price * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = total_value

        return base_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/land-valuation")
async def land_valuation(
    request: LandValuationRequest,
    user=Depends(decode_jwt),  # 🔒 still protected
):
    try:
        return await calculate_land_value(
            city=request.city.lower(),
            state=request.state.lower(),
            sqft=request.sqft,
            road_width=request.road_width,
            zone=request.zone.lower(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
