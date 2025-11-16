CITY_PRICE_DATA = {
    "hyderabad": {
        "avg_price_sqft": 5800,
        "min_price_sqft": 4200,
        "max_price_sqft": 9000,
        "confidence": 0.82
    },
    "bangalore": {
        "avg_price_sqft": 7200,
        "min_price_sqft": 4800,
        "max_price_sqft": 11000,
        "confidence": 0.86
    },
    "mumbai": {
        "avg_price_sqft": 14500,
        "min_price_sqft": 9500,
        "max_price_sqft": 26000,
        "confidence": 0.91
    },
    "chennai": {
        "avg_price_sqft": 6500,
        "min_price_sqft": 4500,
        "max_price_sqft": 9800,
        "confidence": 0.80
    },
    "pune": {
        "avg_price_sqft": 7500,
        "min_price_sqft": 5200,
        "max_price_sqft": 12000,
        "confidence": 0.84
    },
    "delhi": {
        "avg_price_sqft": 12000,
        "min_price_sqft": 8000,
        "max_price_sqft": 19000,
        "confidence": 0.88
    },
    "faridabad": {
        "avg_price_sqft": 5000,
        "min_price_sqft": 3500,
        "max_price_sqft": 8200,
        "confidence": 0.79
    },
    "kolkata": {
        "avg_price_sqft": 5900,
        "min_price_sqft": 4000,
        "max_price_sqft": 8700,
        "confidence": 0.76
    }
}


async def get_city_price(city: str):
    city_lower = city.lower()

    if city_lower in CITY_PRICE_DATA:
        result = CITY_PRICE_DATA[city_lower]
        result["city"] = city.capitalize()
        return result

    return None
