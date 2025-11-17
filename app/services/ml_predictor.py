# app/services/ml_predictor.py

import joblib
import os
import numpy as np

# Load model + encoders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "lightgbm_price_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "..", "models", "label_encoders.pkl")

model = joblib.load(MODEL_PATH)
label_encoders = joblib.load(ENCODER_PATH)


def predict_price(
    city: str,
    state: str,
    sqft: float,
    bedrooms: int,
    bathrooms: int,
    age: float,
    crime_index: float,
    amenities_count: float,
    road_width: float,
    zone: str
):
    """
    Predict total property price using LightGBM.
    """

    # Encode categorical fields
    def encode_safe(encoder, value):
        try:
            return encoder.transform([value])[0]
        except:
            return 0  # fallback if unseen label

    city_encoded = encode_safe(label_encoders["city"], city)
    state_encoded = encode_safe(label_encoders["state"], state)
    zone_encoded = encode_safe(label_encoders["zone"], zone)

    # Create feature array
    features = np.array([[
        city_encoded,
        state_encoded,
        sqft,
        bedrooms,
        bathrooms,
        age,
        crime_index,
        amenities_count,
        road_width,
        zone_encoded
    ]], dtype=float)

    # Predict total price
    prediction = model.predict(features)[0]

    return round(float(prediction), 2)

