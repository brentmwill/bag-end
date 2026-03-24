import httpx
from typing import Any


async def fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
        "forecast_days": 7,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        response.raise_for_status()
        raw = response.json()

    current = raw.get("current_weather", {})
    daily = raw.get("daily", {})

    forecast = []
    dates = daily.get("time", [])
    for i, d in enumerate(dates):
        forecast.append({
            "date": d,
            "max": daily.get("temperature_2m_max", [None])[i],
            "min": daily.get("temperature_2m_min", [None])[i],
            "precip_prob": daily.get("precipitation_probability_max", [None])[i],
            "code": daily.get("weathercode", [None])[i],
        })

    return {
        "current": {
            "temp": current.get("temperature"),
            "weathercode": current.get("weathercode"),
            "windspeed": current.get("windspeed"),
        },
        "forecast": forecast,
    }
