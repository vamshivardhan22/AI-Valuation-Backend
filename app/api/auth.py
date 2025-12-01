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

__all__ = ["verify_jwt"]   # export for protected routes

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Environment Variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")

# Backend callback URL (Google)
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://ai-valuation-backend-1.onrender.com/auth/google/callback"
)

# Redirect user back to frontend with token
FRONTEND_AUTH_SUCCESS_URL = os.getenv(
    "FRONTEND_AUTH_SUCCESS_URL",
    "https://ai-valuation-frontend.vercel.app/auth/callback"
)

security = HTTPBearer()


# =====================================
# JWT Verifier
# =====================================
def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# =====================================
# Google Login
# =====================================
@router.get("/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth is not configured")

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


# =====================================
# Google Callback → generate JWT
# =====================================
@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    token_url = "https://oauth2.googleapis.com/token"

    payload = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
    }

    # Exchange CODE → ACCESS TOKEN
    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=payload)

    token_json = token_res.json()

    if "access_token" not in token_json:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {token_json}")

    access_token = token_json["access_token"]

    # Fetch Google Profile
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    g = user_res.json()

    # Create or Update DB user
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
        algorithm="HS256"
    )

    redirect_url = f"{FRONTEND_AUTH_SUCCESS_URL}?token={jwt_token}"

    return RedirectResponse(redirect_url)


# =====================================
# Authenticated User Details
# =====================================
@router.get("/me")
def auth_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=["HS256"]
        )
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


# =====================================
# Logout (frontend deletes token)
# =====================================
@router.post("/logout")
def logout():
    return {"message": "Logout successful"}
