"""Tests for WeatherSkill."""

import pytest
from unittest.mock import AsyncMock, patch

from handler import WeatherSkill
from zero_bot_sdk import SkillContext, SkillResponse


@pytest.fixture
def skill():
    return WeatherSkill()


@pytest.fixture
def ctx():
    return SkillContext.for_testing(
        config={"api_key": "test-key", "units": "metric"}
    )


@pytest.mark.asyncio
async def test_on_command_weather(skill, ctx):
    """Test /weather command returns weather info."""
    with patch.object(skill, "_get_weather", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "description": "ясно",
            "temp": 25,
            "humidity": 60,
            "wind_speed": 3,
        }
        result = await skill.on_command(ctx, "/weather", "Moscow")
        assert isinstance(result, SkillResponse)
        assert "Moscow" in result.text
        assert "25" in result.text


@pytest.mark.asyncio
async def test_on_command_skip(skill, ctx):
    """Test non-weather command returns skip."""
    result = await skill.on_command(ctx, "/start", "")
    assert result.skip


@pytest.mark.asyncio
async def test_on_message_weather_keyword(skill, ctx):
    """Test natural language weather query."""
    with patch.object(skill, "_get_weather", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "description": "облачно",
            "temp": 18,
            "humidity": 75,
            "wind_speed": 5,
        }
        result = await skill.on_message(ctx, "какая погода в Москве")
        assert isinstance(result, SkillResponse)
        assert not result.skip


@pytest.mark.asyncio
async def test_on_message_skip(skill, ctx):
    """Test non-weather message returns skip."""
    result = await skill.on_message(ctx, "привет как дела")
    assert result.skip


@pytest.mark.asyncio
async def test_on_install(skill, ctx):
    """Test install sets config."""
    await skill.on_install(ctx)
    assert skill.api_key == "test-key"
    assert skill.units == "metric"
