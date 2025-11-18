import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../models/mobilenetv2_damage.onnx")

session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

CLASSES = ["no_damage", "minor_damage", "moderate_damage", "severe_damage"]


def preprocess_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((224, 224))

    arr = np.array(image).astype("float32") / 255.0
    arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, axis=0)

    return arr


def run_damage_detection(image_bytes):
    img = preprocess_image(image_bytes)

    preds = session.run([output_name], {input_name: img})[0]

    class_id = int(np.argmax(preds))
    confidence = float(np.max(preds))

    return {
        "label": CLASSES[class_id],
        "score": class_id,
        "confidence": confidence,
    }
