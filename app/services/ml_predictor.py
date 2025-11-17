import joblib
import numpy as np
import os

# Path to model files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "price_prediction_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "..", "models", "scaler.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "..", "models", "encoder.pkl")

# Load model
model = joblib.load(MODEL_PATH)

# Load scaler (if exists)
scaler = joblib.load(SCALER_PATH) if os.path.exists(SCALER_PATH) else None

# Load encoder (if exists)
encoder = joblib.load(ENCODER_PATH) if os.path.exists(ENCODER_PATH) else None


def predict_price(city, state, sqft, bedrooms, bathrooms, age,
                  crime_index, amenities_count, road_width, zone):
    """
    Takes inputs → prepares ML features → returns predicted price.
    """

    # Prepare input as dataframe-like array (ML expects correct feature order)
    input_data = np.array([[city, state, sqft, bedrooms, bathrooms, age,
                            crime_index, amenities_count, road_width, zone]],
                          dtype=object)

    # Apply label encoding (if available)
    if encoder:
        try:
            input_data[:, 0] = encoder.transform(input_data[:, 0])  # city
            input_data[:, 1] = encoder.transform(input_data[:, 1])  # state
            input_data[:, 9] = encoder.transform(input_data[:, 9])  # zone
        except:
            pass

    # Apply scaling (if available)
    if scaler:
        try:
            input_data = scaler.transform(input_data)
        except:
            pass

    # Predict price_per_sqft
    prediction = model.predict(input_data)[0]

    return float(prediction)
