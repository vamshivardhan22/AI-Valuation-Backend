from fastapi import FastAPI
from app.api.test_apis import router as test_router
from app.api.predict import router as predict_router   # <-- ADD THIS

app = FastAPI(
    title="AI Valuation Backend",
    version="1.0",
    description="Backend server for AI-driven real-time house and land valuation"
)

@app.get("/")
def home():
    return {"status": "Backend Running Successfully"}

app.include_router(test_router)
app.include_router(predict_router)   # <-- ADD THIS
