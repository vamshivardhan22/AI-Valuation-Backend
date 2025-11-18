import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../models/damage_detector.onnx")


# Load ONNX model once
session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)

input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


# Damage labels for this model
LABELS = ["no_damage", "minor_damage", "major_damage"]


def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((224, 224))
    img = np.array(img).astype("float32") / 255.0
    img = np.transpose(img, (2, 0, 1))   # CHW
    img = np.expand_dims(img, axis=0)    # Batch
    return img


def run_damage_detection(image_bytes):
    img = preprocess_image(image_bytes)

    pred = session.run([output_name], {input_name: img})[0]

    index = int(np.argmax(pred))
    score = float(pred[0][index])

    return {
        "label": LABELS[index],
        "score": round(score, 4),
        "confidence": round(score * 100, 2)
    }
