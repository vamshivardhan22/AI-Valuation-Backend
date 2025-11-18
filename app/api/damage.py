# app/api/damage.py

from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.damage_detector import run_damage_detection

router = APIRouter(prefix="/damage", tags=["Damage Detection"])


@router.post("/detect")
async def detect(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(400, "Only JPG/PNG allowed")

        img_bytes = await file.read()
        result = run_damage_detection(img_bytes)

        return {
            "filename": file.filename,
            "damage_label": result["label"],
            "damage_score": result["score"],
            "confidence": result["confidence"]
        }
    except Exception as e:
        raise HTTPException(500, f"Detection failed: {str(e)}")
