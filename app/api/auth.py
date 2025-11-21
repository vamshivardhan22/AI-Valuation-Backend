from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
import jwt
import os
from datetime import datetime

from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")

REDIRECT_URI = os.getenv("REDIRECT_URI")  # Must match Google Console


@router.get("/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth config missing")

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


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    # Validate config
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth config missing")

    token_url = "https://oauth2.googleapis.com/token"

    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_data)

    token_json = token_res.json()

    if "access_token" not in token_json:
        raise HTTPException(status_code=400, detail=f"Google Auth Failed: {token_json}")

    access_token = token_json["access_token"]

    # Fetch user info
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    g_user = user_res.json()

    # Find or create DB user
    user = db.query(User).filter(User.google_id == g_user["id"]).first()

    if user:
        user.last_login = datetime.utcnow()
    else:
        user = User(
            google_id=g_user["id"],
            email=g_user["email"],
            name=g_user.get("name"),
            picture=g_user.get("picture"),
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

    return {
        "token": jwt_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "first_login": user.first_login,
            "last_login": user.last_login,
        }
    }


@router.get("/me")
def auth_me(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
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
        "first_login": user.first_login,
        "last_login": user.last_login,
    }
