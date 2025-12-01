# app/api/auth.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import httpx
import jwt
import os
from datetime import datetime

from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ------------------------
# ENVIRONMENT VARIABLES
# ------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# THE FIX: Use this key consistently
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

JWT_SECRET = os.getenv("JWT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")  # Must be set in Render

security = HTTPBearer()


# ====================================================
# 🔵 STEP 1 — FRONTEND calls:  /auth/google
# ====================================================
@router.get("/google")
async def google_start_oauth():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&access_type=offline"
        "&prompt=consent"
        "&scope=openid%20email%20profile"
    )

    return RedirectResponse(google_auth_url)


# ====================================================
# 🔵 STEP 2 — Google redirects → /auth/google/callback
# ====================================================
@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth config missing")

    # Exchange code → tokens
    token_res = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token_data = token_res.json()

    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail=f"Google token error: {token_data}")

    access_token = token_data["access_token"]

    # Get Google profile
    user_info = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    google_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name")
    picture = user_info.get("picture")

    # Check or create DB user
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            first_login=datetime.utcnow(),
            last_login=datetime.utcnow(),
        )
        db.add(user)
    else:
        user.last_login = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # Create JWT
    jwt_token = jwt.encode(
        {"user_id": user.id, "email": user.email},
        JWT_SECRET,
        algorithm="HS256",
    )

    # Send token to frontend via redirect
    redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}"

    return RedirectResponse(redirect_url)


# ====================================================
# 🔵 GET LOGGED-IN USER
# ====================================================
@router.get("/me")
def get_me(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):

    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
    }


# ====================================================
# 🔵 LOGOUT
# ====================================================
@router.post("/logout")
def logout():
    return {"message": "Logout successful"}
