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

__all__ = ["verify_jwt"]   # <-- EXPORT FIX

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ENV Variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")

security = HTTPBearer()


# ------------------------------------------------------
# JWT Verification Function (used in protect routes)
# ------------------------------------------------------
def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ------------------------------------------------------
# GOOGLE LOGIN
# ------------------------------------------------------
@router.get("/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth not configured")

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&access_type=offline"
        "&prompt=consent"
        "&scope=openid%20email%20profile"
    )

    return RedirectResponse(google_auth_url)


# ------------------------------------------------------
# GOOGLE CALLBACK → JWT → Redirect to Frontend
# ------------------------------------------------------
@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    token_url = "https://oauth2.googleapis.com/token"

    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    # Exchange code
    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_data)

    token_json = token_res.json()

    if "access_token" not in token_json:
        raise HTTPException(status_code=400, detail="OAuth failed")

    access_token = token_json["access_token"]

    # Fetch profile
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    g = user_res.json()

    # DB check/create
    user = db.query(User).filter(User.google_id == g["id"]).first()

    if user:
        user.last_login = datetime.utcnow()
    else:
        user = User(
            google_id=g["id"],
            email=g["email"],
            name=g.get("name"),
            picture=g.get("picture"),
            first_login=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # Create JWT
    jwt_token = jwt.encode(
        {"user_id": user.id, "email": user.email},
        JWT_SECRET,
        algorithm="HS256",
    )

    # REDIRECT TO FRONTEND CALLBACK
    return RedirectResponse(
        f"{FRONTEND_URL}/auth/callback?token={jwt_token}"
    )


# ------------------------------------------------------
# /auth/me
# ------------------------------------------------------
@router.get("/me")
def auth_me(credentials: HTTPAuthorizationCredentials = Depends(security),
            db: Session = Depends(get_db)):

    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/logout")
def logout():
    return {"message": "Logout successful"}
