import onnxruntime as ort
import numpy as np
import joblib
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../models/lgbm_price_model_quant.onnx")
ENCODER_PATH = os.path.join(BASE_DIR, "../models/label_encoders.pkl")

# Load encoders
encoders = joblib.load(ENCODER_PATH)

# Load ONNX runtime session
session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)

input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


def safe_encode(encoder, value):
    """Encode a label safely; fallback to first known label."""
    try:
        return encoder.transform([value])[0]
    except:
        return encoder.transform([encoder.classes_[0]])[0]


def preprocess_input(data: dict):
    """Prepare the input row for ONNX model."""
    x = []

    # Safe categorical encoding
    x.append(safe_encode(encoders["city"], data["city"]))
    x.append(safe_encode(encoders["state"], data["state"]))

    # Numeric
    x.append(float(data["sqft"]))
    x.append(int(data["bedrooms"]))
    x.append(int(data["bathrooms"]))
    x.append(float(data["age"]))
    x.append(float(data["crime_index"]))
    x.append(int(data["amenities_count"]))
    x.append(float(data["road_width"]))

    # Zone (with safe encoding)
    x.append(safe_encode(encoders["zone"], data["zone"]))

    return np.array([x], dtype=np.float32)


def predict_price(**kwargs):
    """Runs the ONNX model prediction."""
    data = dict(kwargs)

    X = preprocess_input(data)

    pred = session.run([output_name], {input_name: X})[0]

    return float(pred[0][0])
