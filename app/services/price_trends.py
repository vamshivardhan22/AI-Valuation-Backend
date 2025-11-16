# app/services/price_trends.py

def calculate_price_trends(
    inflation_rate: float,
    amenities_score: float,
    crime_effect: float
):
    """
    Returns price trends:
    - past 1 year
    - past 5 years
    - next 1 year projection
    - next 5 year projection
    """

    # Convert inflation (4.5) to decimal (0.045)
    inf = inflation_rate / 100

    # --------------------------
    # PAST TRENDS
    # --------------------------

    past_1_year = round(inf * 0.8 * 100, 2)   # % value
    past_5_year = round((inf * 5 * 0.75) * 100, 2)

    # --------------------------
    # FUTURE PROJECTIONS
    # --------------------------

    future_factor = (
        (inf * 0.5) +                   # inflation influence
        (amenities_score * 0.07) -      # amenities boost
        (abs(crime_effect) / 100 * 0.03)  # crime penalty
    )

    projected_1_year = round(future_factor * 100, 2)
    projected_5_year = round((future_factor * 5) * 100, 2)

    return {
        "past_1_year_percent": past_1_year,
        "past_5_years_percent": past_5_year,
        "projected_next_year_percent": projected_1_year,
        "projected_next_5_years_percent": projected_5_year
    }
