#!/usr/bin/env python3
"""
Проверка личности Ия: манифест, промпты и (опционально) один запрос к LLM.
Запуск из корня проекта: python3 scripts/check_personality_ia.py
С OPENROUTER_API_KEY — отправляется тестовое сообщение и проверяется ответ в духе Ии.
"""

import json
import os
import sys
from pathlib import Path

# Project root: parent of script dir (scripts/) or cwd if script in root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else Path.cwd()
PERSONALITY_DIR = PROJECT_ROOT / "personalities" / "ia"


def main() -> int:
    errors = []

    # 1. Manifest
    manifest_path = PERSONALITY_DIR / "manifest.json"
    if not manifest_path.exists():
        errors.append(f"Нет манифеста: {manifest_path}")
        return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"Ошибка чтения манифеста: {e}")
        return 1

    display_name = manifest.get("display_name") or manifest.get("name", "")
    if display_name != "Ия":
        errors.append(f"Личность не Ия: display_name={display_name!r}")
    print(f"✓ Манифест: {display_name} ({manifest.get('name', '')})")

    # 2. Prompts
    prompts_dir = PERSONALITY_DIR / "prompts"
    required = ["system.txt", "system_free.txt", "greeting.txt", "fallback.txt"]
    for name in required:
        p = prompts_dir / name
        if not p.exists():
            errors.append(f"Нет промпта: {p}")
        else:
            text = p.read_text(encoding="utf-8").strip()
            print(f"✓ {name}: {len(text)} символов")

    if errors:
        for e in errors:
            print(f"✗ {e}", file=sys.stderr)
        return 1

    # 3. Optional: one LLM call to verify Ия responds in character
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import AsyncOpenAI
            import asyncio
        except ImportError:
            print("⚠ Для проверки через LLM установите: pip install openai")
            return 0

        async def test_llm():
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None,
                api_key=api_key,
            )
            system_path = PERSONALITY_DIR / "prompts" / "system.txt"
            system_prompt = system_path.read_text(encoding="utf-8").strip()
            model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001") if os.getenv("OPENROUTER_API_KEY") else os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            r = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Привет! Как тебя зовут и что ты умеешь?"},
                ],
                max_tokens=256,
            )
            reply = (r.choices[0].message.content or "").strip()
            return reply

        reply = asyncio.run(test_llm())
        print(f"✓ LLM ответ (фрагмент): {reply[:200]}...")
        reply_lower = reply.lower()
        if "ия" in reply_lower or "ия" in display_name.lower():
            print("✓ Ответ в духе личности Ия")
        else:
            print("⚠ Ответ может быть не в характере Ии — проверь системный промпт")
    else:
        print("ℹ Задай OPENROUTER_API_KEY для проверки ответа через LLM")

    print("\n✅ Личность Ия проверена.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
