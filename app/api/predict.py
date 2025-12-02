from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# JWT Auth (for advanced endpoints)
from app.utils.auth_utils import decode_jwt

# ML price predictor (ONNX LightGBM)
from app.services.ml_predictor import predict_price

# Insights and land valuation services
from app.services.insights_service import (
    get_full_property_insights,
    calculate_price_trends,
)
from app.services.land_valuation import calculate_land_value

# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------
router = APIRouter(prefix="/predict", tags=["Prediction"])

# ------------------------------------------------------------------
# Rent ratio map (used by rent endpoints)
# ------------------------------------------------------------------
RENT_RATIO = {
    "hyderabad": 0.032,  # 3.2% yearly
    "mumbai": 0.028,
    "bangalore": 0.030,
    "delhi": 0.027,
    "chennai": 0.026,
    "pune": 0.029,
    "default": 0.028,
}

# ============================================================
# EXISTING REQUEST MODELS (ADVANCED, JWT PROTECTED)
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
# SIMPLE PUBLIC REQUEST MODELS (MATCH YOUR FRONTEND FORMS)
# ============================================================


class HousePriceRequest(BaseModel):
    area: float
    bedrooms: int
    bathrooms: int
    city: str
    locality: str
    property_type: str
    build_year: Optional[int] = None
    amenities: List[str] = []
    # Optional: if UI sends BHK explicitly; else bedrooms is used
    bhk: Optional[int] = None


class HouseRentRequest(BaseModel):
    area: float
    bedrooms: int
    bathrooms: int
    city: str
    locality: str
    property_type: str
    furnishing: str  # "unfurnished" / "semi-furnished" / "fully-furnished"
    floor: Optional[str] = None
    parking: str  # "yes" / "no"
    amenities: List[str] = []


class LandPriceRequest(BaseModel):
    area: float
    city: str
    locality: str
    zone_type: str  # "residential" / "commercial" / etc.
    road_width: Optional[float] = None
    corner_plot: bool = False


# ============================================================
# HELPER – SAFE ML PREDICTION WRAPPER
# ============================================================


def safe_ml_predict(
    *,
    city: str,
    state: str,
    sqft: float,
    bedrooms: int,
    bathrooms: int,
    age: float,
    crime_index: float,
    amenities_count: int,
    road_width: float,
    zone: str,
):
    """
    Calls the ONNX LightGBM model safely.
    If anything goes wrong, returns a heuristic fallback
    and a reason string for insights.
    """
    try:
        price = predict_price(
            city=city,
            state=state,
            sqft=sqft,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            age=age,
            crime_index=crime_index,
            amenities_count=amenities_count,
            road_width=road_width,
            zone=zone,
        )
        return float(price), ""
    except Exception as e:
        fallback_price = float(sqft) * 5500.0
        reason = f"(Fallback used due to ML error: {e})"
        return fallback_price, reason


# ============================================================
# 1) PUBLIC — /predict/house-price
# ============================================================


@router.post("/house-price")
async def house_price_endpoint(request: HousePriceRequest):
    """
    Lightweight endpoint used by the House Price UI.
    No auth, returns price + range + basic insights.
    """
    city = request.city.lower().strip()
    state = "unknown"  # keep generic; advanced endpoints use real state
    zone = "residential"
    amenities_count = len(request.amenities)

    # Derive age from build_year, with safe default
    current_year = datetime.utcnow().year
    if request.build_year and 1800 < request.build_year <= current_year:
        age = max(0, current_year - request.build_year)
    else:
        age = 10.0  # reasonable default

    # Defaults for now (no UI inputs yet)
    crime_index = 40.0
    road_width = 30.0

    # ML prediction with safe fallback
    base_price, reason = safe_ml_predict(
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

    # Confidence depends on whether fallback was used
    confidence = 0.82 if not reason else 0.55

    min_price = base_price * 0.9
    max_price = base_price * 1.1

    bhk_label = request.bhk if request.bhk is not None else request.bedrooms

    insights = (
        f"Estimated price for {bhk_label} BHK {request.property_type} in "
        f"{request.locality}, {request.city}. "
        f"Area={request.area} sqft, Amenities={amenities_count}, "
        f"Build year={request.build_year or 'NA'}. {reason}"
    )

    return {
        "predicted_price": round(base_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "confidence": confidence,
        "insights": insights,
    }


# ============================================================
# 2) PUBLIC — /predict/house-rent
# ============================================================


@router.post("/house-rent")
async def house_rent_endpoint(request: HouseRentRequest):
    """
    Endpoint for the House Rent page.
    Uses the same ML price estimator + city-wise rent ratio.
    """
    city = request.city.lower().strip()
    state = "unknown"
    zone = "residential"
    amenities_count = len(request.amenities)

    # Simple reasonable defaults for now
    age = 8.0
    crime_index = 50.0
    road_width = 30.0

    # Step 1: property value (via ML + fallback)
    base_price, reason = safe_ml_predict(
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

    # Step 2: yearly → monthly rent using city-wise ratio
    rent_ratio = RENT_RATIO.get(city, RENT_RATIO["default"])
    monthly_rent = (base_price * rent_ratio) / 12

    # Adjust by furnishing
    furnishing = (request.furnishing or "").lower()
    if furnishing.startswith("semi"):
        monthly_rent *= 1.05
    elif furnishing.startswith("full") or furnishing.startswith("fully"):
        monthly_rent *= 1.10

    # Parking effect
    if (request.parking or "").lower() == "yes":
        monthly_rent *= 1.03

    confidence = 0.80 if not reason else 0.60

    insights = (
        f"Estimated rent for {request.property_type} in {request.locality}, {request.city}. "
        f"Area={request.area} sqft, Floor={request.floor or 'NA'}, "
        f"Furnishing={request.furnishing}, Amenities={amenities_count}. {reason}"
    )

    return {
        "monthly_rent": round(monthly_rent, 2),
        "rent_ratio_used": rent_ratio,
        "confidence": confidence,
        "insights": insights,
    }


# ============================================================
# 3) PUBLIC — /predict/land-price
# ============================================================


@router.post("/land-price")
async def land_price_endpoint(request: LandPriceRequest):
    """
    Endpoint for Land Price page.
    Tries your land_valuation service first, then falls back.
    """
    city = request.city.lower().strip()
    state = "unknown"
    zone = request.zone_type.lower()

    road_width = request.road_width if request.road_width is not None else 30.0

    try:
        # Try existing land valuation service
        service_result = await calculate_land_value(
            city=city,
            state=state,
            sqft=request.area,
            road_width=road_width,
            zone=zone,
        )

        base_price = float(service_result.get("estimated_land_value", 0.0))
        confidence = float(service_result.get("confidence", 0.8))
        reason = ""
    except Exception as e:
        # Fallback: simple heuristic
        base_price = float(request.area) * 3000.0
        confidence = 0.65
        reason = f"(Fallback used due to land model error: {e})"

    min_price = base_price * 0.9
    max_price = base_price * 1.1

    insights = (
        f"Estimated value for {request.zone_type} land in {request.locality}, {request.city}. "
        f"Road width={road_width} ft, Corner plot={request.corner_plot}. {reason}"
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
