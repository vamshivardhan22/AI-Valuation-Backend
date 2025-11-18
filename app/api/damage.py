from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.damage_detector import run_damage_detection

router = APIRouter(prefix="/predict", tags=["Damage Detection"])


@router.post("/damage-detection")
async def detect_damage(file: UploadFile = File(...)):
    """
    Upload an image → ONNX MobileNet → Detect damage level.
    """
    try:
        # File validation
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(status_code=400, detail="Only JPG and PNG files are allowed")

        # Read raw image bytes
        image_bytes = await file.read()

        # Run ONNX inference
        result = run_damage_detection(image_bytes)

        return {
            "filename": file.filename,
            "damage_score": result["score"],
            "damage_label": result["label"],
            "confidence": result["confidence"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
