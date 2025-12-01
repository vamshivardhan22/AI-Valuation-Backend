# app/api/predict.py

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
# SIMPLE REQUEST MODELS (for your UI)
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
# HELPERS
# ============================================================

def safe_ml_predict(**kwargs):
    """
    Calls ML model safely.
    If the model crashes, returns heuristic fallback.
    """
    try:
        price = predict_price(**kwargs)
        return float(price), ""
    except Exception as e:
        return float(kwargs["sqft"]) * 5500.0, f"(Fallback used due to ML error: {e})"


# ============================================================
# 1) PUBLIC — /predict/house-price
# ============================================================

@router.post("/house-price")
async def house_price_endpoint(request: HousePriceRequest):
    city = request.city.lower().strip()
    state = "unknown"
    zone = "residential"
    amenities_count = len(request.amenities)

    current_year = datetime.utcnow().year
    if request.build_year and 1800 < request.build_year <= current_year:
        age = max(0, current_year - request.build_year)
    else:
        age = 10.0

    crime_index = 40.0
    road_width = 30.0

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

    min_price = base_price * 0.9
    max_price = base_price * 1.1

    insights = (
        f"Estimated price for {request.bhk} {request.property_type} in "
        f"{request.locality}, {request.city}. "
        f"Amenities={amenities_count}, Build year={request.build_year}. {reason}"
    )

    return {
        "predicted_price": round(base_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "confidence": 0.82,
        "insights": insights,
    }


# ============================================================
# 2) PUBLIC — /predict/house-rent
# ============================================================

@router.post("/house-rent")
async def house_rent_endpoint(request: HouseRentRequest):
    city = request.city.lower().strip()
    amenities_count = len(request.amenities)

    base_price, _ = safe_ml_predict(
        city=city,
        state="unknown",
        sqft=request.area,
        bedrooms=request.bedrooms,
        bathrooms=request.bathrooms,
        age=8.0,
        crime_index=50.0,
        amenities_count=amenities_count,
        road_width=30.0,
        zone="residential",
    )

    rent_ratio = RENT_RATIO.get(city, RENT_RATIO["default"])
    monthly_rent = (base_price * rent_ratio) / 12

    # adjust by furnishing
    if request.furnishing.lower().startswith("semi"):
        monthly_rent *= 1.05
    elif request.furnishing.lower().startswith("full"):
        monthly_rent *= 1.10

    # parking
    if request.parking.lower() == "yes":
        monthly_rent *= 1.03

    min_rent = monthly_rent * 0.9
    max_rent = monthly_rent * 1.1

    insights = (
        f"Estimated rent for {request.property_type} in {request.locality}, {request.city}. "
        f"Floor={request.floor}, Amenities={amenities_count}."
    )

    return {
        "predicted_rent": round(monthly_rent, 2),
        "min_rent": round(min_rent, 2),
        "max_rent": round(max_rent, 2),
        "confidence": 0.78,
        "insights": insights,
    }


# ============================================================
# 3) PUBLIC — /predict/land-price
# ============================================================

@router.post("/land-price")
async def land_price_endpoint(request: LandPriceRequest):
    city = request.city.lower().strip()
    zone = request.zone_type.lower()

    try:
        service_result = await calculate_land_value(
            city=city,
            state="unknown",
            sqft=request.area,
            road_width=request.road_width or 30.0,
            zone=zone,
        )
        base_price = float(service_result.get("estimated_land_value", 0.0))
        confidence = float(service_result.get("confidence", 0.8))
        reason = ""
    except Exception as e:
        base_price = float(request.area) * 3000.0
        confidence = 0.65
        reason = f"(Fallback used due to land model error: {e})"

    min_price = base_price * 0.9
    max_price = base_price * 1.1

    insights = (
        f"Estimated value for {request.zone_type} land in {request.locality}, {request.city}. "
        f"Road width={request.road_width}, Corner plot={request.corner_plot}. {reason}"
    )

    return {
        "predicted_price": round(base_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "confidence": confidence,
        "insights": insights,
    }
