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

__all__ = ["verify_jwt"]

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ------------------------------------------------------
# ENV VARIABLES
# ------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret")

# Backend Google OAuth Redirect URI
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://ai-valuation-backend-1.onrender.com/auth/google/callback"
)

# After token creation redirect user to frontend
FRONTEND_AUTH_SUCCESS_URL = os.getenv(
    "FRONTEND_AUTH_SUCCESS_URL",
    "https://ai-valuation-frontend.vercel.app/auth/callback"
)

security = HTTPBearer()

# ------------------------------------------------------
# JWT VERIFY (Protected routes)
# ------------------------------------------------------
def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ------------------------------------------------------
# STEP 1 — Send user to Google Auth
# ------------------------------------------------------
@router.get("/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth not configured")

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&access_type=offline"
        "&prompt=consent"
        "&include_granted_scopes=true"
        "&scope=openid%20email%20profile"
    )

    return RedirectResponse(google_auth_url)


# ------------------------------------------------------
# STEP 2 — Google sends BACK `?code=XXXX`
# Backend exchanges this code → access token → user info
# ------------------------------------------------------
@router.get("/google/callback")
async def google_callback(code: str = None, db: Session = Depends(get_db)):
    # If code missing, DO NOT redirect again (prevents infinite loop)
    if not code:
        raise HTTPException(
            status_code=400,
            detail="Missing OAuth code from Google. Check redirect URL settings."
        )

    token_url = "https://oauth2.googleapis.com/token"

    token_request_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_request_data)

    token_json = token_res.json()

    if "access_token" not in token_json:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth token exchange failed: {token_json}"
        )

    access_token = token_json["access_token"]

    # Fetch profile
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    profile = user_res.json()

    if "id" not in profile:
        raise HTTPException(
            status_code=400,
            detail=f"User profile fetch failed: {profile}"
        )

    # Save or update user
    user = db.query(User).filter(User.google_id == profile["id"]).first()

    if not user:
        user = User(
            google_id=profile["id"],
            email=profile.get("email"),
            name=profile.get("name"),
            picture=profile.get("picture"),
            first_login=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        db.add(user)
    else:
        user.last_login = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # Build JWT Token
    jwt_token = jwt.encode(
        {"user_id": user.id, "email": user.email},
        JWT_SECRET,
        algorithm="HS256"
    )

    final_url = f"{FRONTEND_AUTH_SUCCESS_URL}?token={jwt_token}"

    # FULL STOP — final redirect to frontend
    return RedirectResponse(final_url)


# ------------------------------------------------------
# /auth/me (protected)
# ------------------------------------------------------
@router.get("/me")
def auth_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "first_login": user.first_login,
        "last_login": user.last_login,
    }


# ------------------------------------------------------
# Logout
# ------------------------------------------------------
@router.post("/logout")
def logout():
    return {"message": "Logout successful"}
