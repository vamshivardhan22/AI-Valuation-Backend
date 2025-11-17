import onnxruntime as ort
import numpy as np
import joblib
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../models/lgbm_price_model_quant.onnx")
ENCODER_PATH = os.path.join(BASE_DIR, "../models/label_encoders.pkl")

# Load label encoders
encoders = joblib.load(ENCODER_PATH)

# Load ONNX model
session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)

# Extract input/output node names
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


def preprocess_input(data: dict):
    """Encode categorical fields & prepare model array."""
    x = []

    # Encode categorical
    x.append(encoders["city"].transform([data["city"]])[0])
    x.append(encoders["state"].transform([data["state"]])[0])
    
    # Numeric values
    x.append(float(data["sqft"]))
    x.append(int(data["bedrooms"]))
    x.append(int(data["bathrooms"]))
    x.append(float(data["age"]))
    x.append(float(data["crime_index"]))
    x.append(int(data["amenities_count"]))
    x.append(float(data["road_width"]))

    # Encode zone
    x.append(encoders["zone"].transform([data["zone"]])[0])

    return np.array([x], dtype=np.float32)


def predict_price(**kwargs):
    """
    Accepts keyword arguments from predict.py
    Converts to dict internally.
    """
    data = dict(kwargs)

    inputs = preprocess_input(data)

    pred = session.run([output_name], {input_name: inputs})[0]

    return float(pred[0][0])
