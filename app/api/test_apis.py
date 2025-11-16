from fastapi import APIRouter

# ALL IMPORTS MUST BE AT TOP
from app.services.geocode import get_coordinates
from app.services.inflation import get_inflation
from app.services.amenities import get_amenities
from app.services.crime import get_crime_rate
from app.services.sales import get_recent_sales
from app.services.city_price import get_city_price

router = APIRouter(prefix="/test", tags=["Test APIs"])


@router.get("/geocode")
async def geocode(location: str):
    result = await get_coordinates(location)
    if result is None:
        return {"error": "Location not found"}
    return result


@router.get("/inflation")
async def inflation(country_code: str):
    data = await get_inflation(country_code.upper())
    if data is None:
        return {"error": "Invalid country code or no inflation data"}
    return data


@router.get("/amenities")
async def amenities(lat: float, lon: float, radius: int = 2000):
    results = await get_amenities(lat, lon, radius)
    return {"count": len(results), "results": results}


@router.get("/crime")
async def crime(city: str):
    result = await get_crime_rate(city)
    if result is None:
        return {"error": "Crime data not available"}
    return result


@router.get("/recent-sales")
async def recent_sales(lat: float, lon: float, radius: int = 2000):
    data = await get_recent_sales(lat, lon, radius)
    return {
        "count": len(data),
        "sales": data
    }


@router.get("/city-price")
async def city_price(city: str):
    data = await get_city_price(city)
    if data is None:
        return {"error": "City price not available"}
    return data
