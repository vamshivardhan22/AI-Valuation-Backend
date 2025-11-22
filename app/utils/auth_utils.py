import jwt
from fastapi import HTTPException, Header
import os

JWT_SECRET = os.getenv("JWT_SECRET")


def decode_jwt(token: str = Header(None)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
