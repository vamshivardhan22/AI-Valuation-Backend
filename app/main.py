from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models.user import User

Base.metadata.create_all(bind=engine)

# Routers
from app.api.test_apis import router as test_router
from app.api.predict import router as predict_router
from app.api.damage import router as damage_router
from app.api.auth import router as auth_router

app = FastAPI(
    title="AI Valuation Backend",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Backend Running"}

app.include_router(test_router)
app.include_router(predict_router)
app.include_router(damage_router)
app.include_router(auth_router)
