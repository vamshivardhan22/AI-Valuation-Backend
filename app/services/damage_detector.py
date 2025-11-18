# app/services/damage_detector.py

import os
import onnxruntime as ort
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../models/damage_detector.onnx")

# Load ONNX model
session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)

input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


def preprocess_image(image: Image.Image):
    """Resize + normalize image for MobileNetV2 ONNX."""
    image = image.resize((224, 224))
    image = image.convert("RGB")

    img = np.array(image).astype("float32") / 255.0

    # Normalize like ImageNet
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])

    img = (img - mean) / std

    # HWC → CHW
    img = np.transpose(img, (0, 1, 2))[np.newaxis, :]
    return img.astype(np.float32)


def predict_damage(image: Image.Image):
    """Run ONNX model and return top predictions."""
    x = preprocess_image(image)

    pred = session.run([output_name], {input_name: x})[0][0]

    # Convert logits → probabilities
    exp = np.exp(pred - np.max(pred))
    probs = exp / exp.sum()

    # Top-3 predictions
    top_idx = probs.argsort()[-3:][::-1]

    return [
        {
            "class_id": int(i),
            "confidence": float(probs[i])
        }
        for i in top_idx
    ]
