"""OpenWeatherMap tool for weather forecasts."""

from typing import Any

import requests

from app.config import settings
from app.tools.base import BaseTool, ToolParameter

OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5"


class GetWeatherForecastTool(BaseTool):
    """Tool for getting weather forecast."""

    @property
    def name(self) -> str:
        return "get_weather_forecast"

    @property
    def description(self) -> str:
        return (
            "Get weather forecast for a specific location. "
            "Returns temperature, weather condition, precipitation probability, "
            "and other weather data for the next 5 days."
        )

    @property
    def parameters(self) -> dict[str, ToolParameter]:
        return {
            "city": ToolParameter(
                type="string",
                description="City name (e.g., 'Seoul', 'Tokyo', 'New York')",
            ),
            "country_code": ToolParameter(
                type="string",
                description="ISO 3166 country code (e.g., 'KR', 'JP', 'US')",
                default="",
            ),
            "units": ToolParameter(
                type="string",
                description="Units for temperature",
                enum=["metric", "imperial"],
                default="metric",
            ),
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Get weather forecast.

        Args:
            city: City name.
            country_code: ISO country code (optional).
            units: Temperature units (metric/imperial).

        Returns:
            Weather forecast data.
        """
        city = kwargs["city"]
        country_code = kwargs.get("country_code", "")
        units = kwargs.get("units", "metric")

        if not settings.openweathermap_api_key:
            return {
                "success": False,
                "error": "OpenWeatherMap API key not configured",
            }

        try:
            # Build location query
            location = city
            if country_code:
                location = f"{city},{country_code}"

            # Get 5-day forecast
            response = requests.get(
                f"{OPENWEATHERMAP_BASE_URL}/forecast",
                params={
                    "q": location,
                    "appid": settings.openweathermap_api_key,
                    "units": units,
                    "cnt": 40,  # 5 days * 8 (3-hour intervals)
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # Process forecast data
            forecasts = self._process_forecast(data, units)

            return {
                "success": True,
                "location": {
                    "city": data["city"]["name"],
                    "country": data["city"]["country"],
                },
                "forecasts": forecasts,
                "units": {
                    "temperature": "°C" if units == "metric" else "°F",
                    "wind_speed": "m/s" if units == "metric" else "mph",
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"City not found: {city}",
                }
            return {
                "success": False,
                "error": f"API error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _process_forecast(
        self, data: dict, units: str
    ) -> list[dict[str, Any]]:
        """Process raw forecast data into daily summaries."""
        daily_forecasts: dict[str, list] = {}

        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            if date not in daily_forecasts:
                daily_forecasts[date] = []
            daily_forecasts[date].append(item)

        forecasts = []
        for date, items in daily_forecasts.items():
            temps = [item["main"]["temp"] for item in items]
            feels_like = [item["main"]["feels_like"] for item in items]
            humidity = [item["main"]["humidity"] for item in items]

            # Get precipitation probability (if available)
            pop = [item.get("pop", 0) * 100 for item in items]

            # Get most common weather condition
            conditions = [item["weather"][0]["main"] for item in items]
            main_condition = max(set(conditions), key=conditions.count)

            descriptions = [item["weather"][0]["description"] for item in items]
            main_description = max(set(descriptions), key=descriptions.count)

            forecasts.append({
                "date": date,
                "temperature": {
                    "min": round(min(temps), 1),
                    "max": round(max(temps), 1),
                    "avg": round(sum(temps) / len(temps), 1),
                },
                "feels_like": {
                    "min": round(min(feels_like), 1),
                    "max": round(max(feels_like), 1),
                },
                "humidity_avg": round(sum(humidity) / len(humidity)),
                "precipitation_probability": round(max(pop)),
                "condition": main_condition,
                "description": main_description,
            })

        return forecasts