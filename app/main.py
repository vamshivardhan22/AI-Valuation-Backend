from fastapi import FastAPI

from app.api.test_apis import router as test_router
from app.api.predict import router as predict_router
from app.api.damage import router as damage_router

app = FastAPI(
    title="AI Valuation Backend",
    version="1.0",
    description="Backend for AI-powered valuation + ML + ONNX Damage Detection",
)

@app.get("/")
def home():
    return {"status": "Backend Running Successfully"}

app.include_router(test_router)
app.include_router(predict_router)
app.include_router(damage_router)
