from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import jwt
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")

# FIXED: Correct env variable name
REDIRECT_URI = os.getenv("REDIRECT_URI")


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
async def google_callback(code: str):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OAuth config missing")

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=data)

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

    user = user_res.json()

    # Create JWT
    jwt_token = jwt.encode(
        {"email": user["email"], "name": user.get("name")},
        JWT_SECRET,
        algorithm="HS256",
    )

    return {"token": jwt_token, "user": user}
