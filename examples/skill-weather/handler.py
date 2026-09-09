"""
Weather Forecast Skill for Zero Bot.
Get weather forecasts for any city worldwide.
"""

from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse


class WeatherSkill(BaseSkill):
    """Weather forecast skill using OpenWeatherMap API."""

    name = "weather-forecast"
    version = "1.0.0"

    async def on_install(self, ctx: SkillContext) -> None:
        """Called once when skill is installed on a bot."""
        self.api_key = ctx.config.get("api_key", "")
        self.units = ctx.config.get("units", "metric")

    async def on_command(self, ctx: SkillContext, command: str, args: str) -> SkillResponse:
        """Handle /weather command."""
        if command == "/weather":
            city = args.strip() or "Moscow"
            weather = await self._get_weather(city)
            temperature_unit = "°C" if self.units == "metric" else "°F"
            return SkillResponse(
                text=f"🌤 **{city}**\n\n"
                     f"{weather['description']}\n"
                     f"🌡 {weather['temp']}{temperature_unit}\n"
                     f"💧 Влажность: {weather['humidity']}%\n"
                     f"💨 Ветер: {weather['wind_speed']} м/s"
            )
        return SkillResponse.skip()

    async def on_message(self, ctx: SkillContext, text: str) -> SkillResponse:
        """Handle natural language weather queries."""
        weather_keywords = ["погода", "weather", "forecast", "прогноз"]
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in weather_keywords):
            city = self._extract_city(text)
            if city:
                weather = await self._get_weather(city)
                temperature_unit = "°C" if self.units == "metric" else "°F"
                return SkillResponse(
                    text=f"🌤 **{city}**: {weather['description']}, {weather['temp']}{temperature_unit}"
                )

        return SkillResponse.skip()

    async def on_uninstall(self, ctx: SkillContext) -> None:
        """Cleanup when skill is removed."""
        pass

    async def _get_weather(self, city: str) -> dict:
        """Fetch weather from OpenWeatherMap API."""
        import httpx

        if not self.api_key:
            return {
                "description": "⚠️ API ключ не настроен",
                "temp": "?",
                "humidity": "?",
                "wind_speed": "?",
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": city,
                        "appid": self.api_key,
                        "units": self.units,
                        "lang": "ru",
                    },
                )
                data = resp.json()
                return {
                    "description": data["weather"][0]["description"],
                    "temp": round(data["main"]["temp"]),
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"],
                }
        except Exception:
            return {
                "description": "⚠️ Не удалось получить данные",
                "temp": "?",
                "humidity": "?",
                "wind_speed": "?",
            }

    def _extract_city(self, text: str) -> str | None:
        """Try to extract city name from message."""
        import re
        # Simple extraction: look for city after keywords
        patterns = [
            r"(?:погода|weather|forecast|прогноз)\s+(?:в\s+|in\s+)?([а-яА-ЯёЁa-zA-Z\s-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip().title()
        return None
