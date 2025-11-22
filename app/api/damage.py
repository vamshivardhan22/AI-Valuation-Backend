# app/api/damage.py

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from app.services.damage_detector import run_damage_detection
from app.api.auth import verify_jwt  # ✅ JWT protection

router = APIRouter(prefix="/damage", tags=["Damage Detection"])


@router.post("/detect")
async def detect(
    file: UploadFile = File(...),
    user=Depends(verify_jwt)   # ✅ Protect route with JWT
):
    """
    Protected damage detection route.
    Requires JWT token to access.
    """
    try:
        # Validate image type
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(status_code=400, detail="Only JPG/PNG allowed")

        # Read file
        img_bytes = await file.read()

        # Run AI model
        result = run_damage_detection(img_bytes)

        return {
            "filename": file.filename,
            "damage_label": result["label"],
            "damage_score": result["score"],
            "confidence": result["confidence"],
            "user": user  # optional info, can be removed
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
