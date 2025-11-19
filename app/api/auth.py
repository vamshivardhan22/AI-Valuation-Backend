from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
import httpx
import jwt
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


@router.get("/google/login")
async def google_login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20profile%20email"
    )
    return RedirectResponse(google_auth_url)


@router.get("/google/callback")
async def google_callback(code: str):
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

    if "access_token" not in token_res.json():
        raise HTTPException(status_code=400, detail="Google Auth Failed")

    access_token = token_res.json()["access_token"]

    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    user = user_res.json()

    jwt_token = jwt.encode(
        {"email": user["email"], "name": user.get("name")},
        JWT_SECRET,
        algorithm="HS256"
    )

    return {"token": jwt_token, "user": user}
