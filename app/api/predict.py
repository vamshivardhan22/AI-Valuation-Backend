# app/api/predict.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import joblib
import onnxruntime as ort

# Existing Services
from app.services.combined_model import get_full_property_insights
from app.services.land_valuation import calculate_land_value
from app.services.price_trends import calculate_price_trends


router = APIRouter(prefix="/predict", tags=["Valuation"])

# =====================================
# Load Encoders + ONNX Quantized Model
# =====================================
ENCODER_PATH = "app/models/label_encoders.pkl"
MODEL_PATH = "app/models/lgbm_price_model_quant.onnx"

encoders = joblib.load(ENCODER_PATH)

session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)

# ===========================
# Rent Ratio Mapping
# ===========================
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

# ===============================
# Request Models
# ===============================

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


# =============================================
# Helper: Encode categorical inputs
# =============================================
def encode_input(data: dict):
    processed = data.copy()

    for col, le in encoders.items():
        if col in processed:
            processed[col] = le.transform([processed[col]])[0]

    return processed


# =============================================
# ONNX Prediction Function
# =============================================
def onnx_predict_price(**kwargs):

    data_enc = encode_input(kwargs)

    features = np.array([[
        data_enc["city"],
        data_enc["state"],
        data_enc["sqft"],
        data_enc["bedrooms"],
        data_enc["bathrooms"],
        data_enc["age"],
        data_enc["crime_index"],
        data_enc["amenities_count"],
        data_enc["road_width"],
        data_enc["zone"],
    ]], dtype=np.float32)

    inputs = {session.get_inputs()[0].name: features}
    prediction = session.run(None, inputs)[0]

    return float(prediction[0][0])


# =====================================================================
# 🔥 FULL PROPERTY VALUATION ENDPOINT (AI + Rent + Price Trends + ML)
# =====================================================================
@router.post("/property-valuation")
async def property_valuation(request: FullPropertyRequest):
    try:
        # 1. Base insights using your combined model
        base_result = await get_full_property_insights(
            city=request.city,
            state=request.state,
            crime_index=request.crime_index
        )

        price_per_sqft = base_result["pricing"]["final_price_per_sqft"]
        total_value = round(price_per_sqft * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = total_value

        # 2. Rent Estimation
        city_lower = request.city.lower()
        rent_ratio = RENT_RATIO.get(city_lower, RENT_RATIO["default"])

        yearly_rent = total_value * rent_ratio
        monthly_rent = yearly_rent / 12

        amenities_score = base_result["pricing"]["amenities_score"]
        crime_effect = base_result["pricing"]["crime_effect_percent"]
        inflation = base_result["pricing"]["inflation_adjustment_percent"]

        monthly_rent *= (1 + amenities_score * 0.10)

        if crime_effect < 0:
            monthly_rent *= (1 - abs(crime_effect) / 100)

        monthly_rent *= (1 + inflation / 200)
        monthly_rent = round(monthly_rent, 2)

        rent_confidence = round(
            (base_result["overall_confidence"] * 0.7)
            + (amenities_score * 0.3), 2
        )

        base_result["pricing"]["rent_estimate"] = {
            "monthly_rent": monthly_rent,
            "rent_ratio_used": rent_ratio,
            "rent_confidence": rent_confidence
        }

        # 3. Price Trends
        trends = calculate_price_trends(
            inflation_rate=inflation,
            amenities_score=amenities_score,
            crime_effect=crime_effect
        )
        base_result["pricing"]["price_trends"] = trends

        # -----------------------------------------------------
        # 4. ONNX LightGBM ML Model Prediction (FINAL ML PRICE)
        # -----------------------------------------------------
        ml_price = onnx_predict_price(
            city=request.city,
            state=request.state,
            sqft=request.sqft,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            age=request.age,
            crime_index=request.crime_index,
            amenities_count=request.amenities_count,
            road_width=request.road_width,
            zone=request.zone
        )

        base_result["ml_predicted_price"] = ml_price

        return base_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property valuation failed: {str(e)}")


# =============================================
# BASIC VALUATION ENDPOINT
# =============================================
@router.post("/valuation")
async def valuation(request: ValuationRequest):
    try:
        base_result = await get_full_property_insights(
            city=request.city,
            state=request.state,
            crime_index=request.crime_index
        )

        price_per_sqft = base_result["pricing"]["final_price_per_sqft"]
        total_value = round(price_per_sqft * request.sqft, 2)

        base_result["pricing"]["sqft"] = request.sqft
        base_result["pricing"]["total_property_value"] = total_value

        return base_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation failed: {str(e)}")


# =============================================
# LAND VALUATION
# =============================================
@router.post("/land-valuation")
async def land_valuation(request: LandValuationRequest):
    try:
        return await calculate_land_value(
            city=request.city,
            state=request.state,
            sqft=request.sqft,
            road_width=request.road_width,
            zone=request.zone
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Land valuation failed: {str(e)}")
