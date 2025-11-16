import httpx

# --------------------
# Fetch live CPI data
# --------------------
async def get_inflation(country_code: str = "IN"):
    """
    Fetch latest CPI inflation from World Bank API.
    Falls back to None if data unavailable.
    """
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/FP.CPI.TOTL?format=json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            if not data or len(data) < 2 or not data[1]:
                return None

            latest_record = data[1][0]

            return {
                "country": latest_record.get("country", {}).get("value"),
                "year": latest_record.get("date"),
                "cpi": latest_record.get("value")
            }

    except Exception:
        return None



# -------------------------------
# SIMPLE INFLATION ADJUSTMENT
# (Used by combined_model.py)
# -------------------------------
def get_inflation_adjustment():
    """
    Returns a simple inflation adjustment %.
    For now, returns a fixed 4.5% which is realistic for India.
    Later we can convert CPI to inflation automatically.
    """
    return 4.5  # safe default fallback
