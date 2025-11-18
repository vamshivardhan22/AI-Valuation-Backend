from fastapi import FastAPI

# Existing routers
from app.api.test_apis import router as test_router
from app.api.predict import router as predict_router

# NEW damage detection router
from app.api.damage import router as damage_router


app = FastAPI(
    title="AI Valuation Backend",
    version="1.0",
    description="Backend server for AI-driven real-time house and land valuation"
)

@app.get("/")
def home():
    return {"status": "Backend Running Successfully"}

# Include routers
app.include_router(test_router)
app.include_router(predict_router)
app.include_router(damage_router)   # <--- IMPORTANT
