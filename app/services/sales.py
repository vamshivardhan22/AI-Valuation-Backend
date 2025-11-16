import httpx

async def get_recent_sales(lat: float, lon: float, radius: int = 2000):
    url = "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json];
    (
      node["real_estate:price"](around:{radius},{lat},{lon});
      node["addr:price"](around:{radius},{lat},{lon});
      node["price:sqft"](around:{radius},{lat},{lon});
      node["price:sqm"](around:{radius},{lat},{lon});
    );
    out center;
    """

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, data={"data": query})
        data = response.json()

        return data.get("elements", [])
