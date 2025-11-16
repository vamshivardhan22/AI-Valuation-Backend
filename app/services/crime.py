# OFFLINE CRIME DATA (Temporary)
# Replace with India Gov API later

CRIME_DATA = [
    {"city": "Hyderabad", "state": "Telangana", "crime_index": 43.4},
    {"city": "Mumbai", "state": "Maharashtra", "crime_index": 45.8},
    {"city": "Delhi", "state": "Delhi", "crime_index": 60.6},
    {"city": "Chennai", "state": "Tamil Nadu", "crime_index": 39.3},
    {"city": "Bangalore", "state": "Karnataka", "crime_index": 49.9},
    {"city": "Bengaluru", "state": "Karnataka", "crime_index": 49.9},
    {"city": "Kolkata", "state": "West Bengal", "crime_index": 38.3},
    {"city": "Pune", "state": "Maharashtra", "crime_index": 44.2},
    {"city": "Jaipur", "state": "Rajasthan", "crime_index": 42.1}
]

async def get_crime_rate(city: str):
    city_lower = city.lower()
    for record in CRIME_DATA:
        if record["city"].lower() == city_lower:
            return record
    return None


def get_crime_impact(crime_index: float) -> float:
    """
    Convert crime index to a percentage impact on property price.
    Higher crime = negative impact.
    Example:
      - Crime index 40 → -4%
      - Crime index 60 → -9%
    """
    # Basic linear mapping
    if crime_index <= 30:
        return -2.0
    elif crime_index <= 40:
        return -4.0
    elif crime_index <= 50:
        return -6.0
    elif crime_index <= 60:
        return -9.0
    else:
        return -12.0
