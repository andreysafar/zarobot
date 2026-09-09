#!/usr/bin/env bash
#
# Копирует скилл helper-kb в каталог навыков бота-хелпера.
#
#   ./scripts/install_helper_skill.sh [volume_бота]
#
# По умолчанию volume: helper_bot_data (бота-хелпера из docker-compose).
# Скрипт работает с любым контейнером, у которого смонтирован /data.
#
set -euo pipefail

VOLUME="${1:-helper_bot_data}"
SKILL_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/examples/skill-helper-kb"

if [[ ! -d "$SKILL_SRC" ]]; then
    echo "✗ Не найден каталог скилла: $SKILL_SRC" >&2
    exit 1
fi

if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    echo "✗ Docker-том '$VOLUME' не найден." >&2
    echo "  Сначала поднимите бота: docker compose up -d helper-bot" >&2
    exit 1
fi

echo "→ Устанавливаю helper-kb в том '$VOLUME'..."

# Копируем через временный контейнер: так не зависим от путей на хосте.
docker run --rm \
    -v "$SKILL_SRC:/src:ro" \
    -v "$VOLUME:/data" \
    alpine:3.19 \
    sh -c 'rm -rf /data/skills/helper-kb \
        && mkdir -p /data/skills \
        && cp -r /src /data/skills/helper-kb \
        && rm -rf /data/skills/helper-kb/tests /data/skills/helper-kb/__pycache__ \
        && ls /data/skills/helper-kb'

echo "✓ Готово. Перезапустите бота: docker compose restart helper-bot"
