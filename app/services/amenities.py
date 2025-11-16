import httpx

async def get_amenities(lat: float, lon: float, radius: int = 2000):
    overpass_url = "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:{radius},{lat},{lon});
      node["amenity"="clinic"](around:{radius},{lat},{lon});
      node["amenity"="pharmacy"](around:{radius},{lat},{lon});
      node["shop"](around:{radius},{lat},{lon});
      node["amenity"="police"](around:{radius},{lat},{lon});
      node["public_transport"](around:{radius},{lat},{lon});
      node["amenity"="bus_station"](around:{radius},{lat},{lon});
      node["amenity"="train_station"](around:{radius},{lat},{lon});
    );
    out center;
    """

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(overpass_url, data={"data": query})
        data = response.json()

        elements = data.get("elements", [])

        # -----------------------------------------
        # COUNTERS FOR EACH AMENITY CATEGORY
        # -----------------------------------------
        counts = {
            "hospitals": 0,
            "clinics": 0,
            "pharmacies": 0,
            "shops": 0,
            "police": 0,
            "public_transport": 0,
            "bus_stations": 0,
            "train_stations": 0
        }

        # -----------------------------------------
        # LOOP THROUGH EACH NODE AND COUNT AMENITIES
        # -----------------------------------------
        for e in elements:
            tags = e.get("tags", {})

            # Hospitals
            if tags.get("amenity") == "hospital":
                counts["hospitals"] += 1

            # Clinics
            elif tags.get("amenity") == "clinic":
                counts["clinics"] += 1

            # Pharmacies
            elif tags.get("amenity") == "pharmacy":
                counts["pharmacies"] += 1

            # Shops
            elif tags.get("shop") is not None:
                counts["shops"] += 1

            # Police stations
            elif tags.get("amenity") == "police":
                counts["police"] += 1

            # Public transport nodes
            elif "public_transport" in tags:
                counts["public_transport"] += 1

            # Bus stations
            elif tags.get("amenity") == "bus_station":
                counts["bus_stations"] += 1

            # Train stations
            elif tags.get("amenity") == "train_station":
                counts["train_stations"] += 1

        # -----------------------------------------
        # TOTAL AMENITIES
        # -----------------------------------------
        total = sum(counts.values())

        # -----------------------------------------
        # AMENITIES SCORE (0 to 1)
        # Higher total amenities = higher score
        # -----------------------------------------
        amenities_score = min(1.0, total / 40)

        # FINAL STRUCTURED RETURN
        return {
            "counts": counts,
            "total": total,
            "score": amenities_score
        }
