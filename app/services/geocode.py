import httpx

async def get_coordinates(location: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }

    headers = {"User-Agent": "AI-Valuation-App"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        data = response.json()

        if not data:
            return None
        
        return {
            "latitude": data[0]["lat"],
            "longitude": data[0]["lon"]
        }
