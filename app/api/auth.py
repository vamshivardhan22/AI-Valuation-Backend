# app/api/auth.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
import os
import jwt
from datetime import datetime, timedelta


router = APIRouter(prefix="/auth", tags=["Google Login"])


# Load secrets from environment (Render Dashboard → Environment)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")  # Example: https://yourbackend.onrender.com/auth/callback
JWT_SECRET = os.getenv("JWT_SECRET")  # random 32 chars


# -----------------------------------------------------------
# 1️⃣ Google Login URL
# -----------------------------------------------------------
@router.get("/login")
def google_login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=consent"
    )
    return {"auth_url": google_auth_url}


# -----------------------------------------------------------
# 2️⃣ Callback — Google sends ?code=
# -----------------------------------------------------------
@router.get("/callback")
async def google_callback(code: str):
    try:
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"

        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=data)
            token_data = token_response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token.")

        # Fetch User Info
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        async with httpx.AsyncClient() as client:
            userinfo = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

        user_data = userinfo.json()

        email = user_data.get("email")
        name = user_data.get("name")
        picture = user_data.get("picture")

        # -----------------------------------------------------------
        # 3️⃣ Create JWT Token (valid for 7 days)
        # -----------------------------------------------------------
        payload = {
            "email": email,
            "name": name,
            "picture": picture,
            "exp": datetime.utcnow() + timedelta(days=7)
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {
            "success": True,
            "token": token,
            "user": {
                "email": email,
                "name": name,
                "picture": picture
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth failed: {str(e)}")

