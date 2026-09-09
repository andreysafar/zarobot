"""
Bot Container Manager.
Manages Docker containers for bot instances via Docker SDK.
"""

import os
import uuid
from typing import Optional, Dict, Any, List

import docker
from loguru import logger


class BotContainerManager:
    """Управление Docker-контейнерами ботов."""

    NETWORK = "zero_bot_net"
    BOT_IMAGE = "zero-bot/bot-instance:latest"

    def __init__(self):
        try:
            self.client = docker.from_env()
            self._ensure_network()
        except docker.errors.DockerException as e:
            logger.error(f"Docker connection failed: {e}")
            raise RuntimeError(f"Docker not available: {e}")

    def _ensure_network(self):
        """Ensure the bot network exists."""
        try:
            self.client.networks.get(self.NETWORK)
        except docker.errors.NotFound:
            self.client.networks.create(self.NETWORK, driver="bridge")
            logger.info(f"Created Docker network: {self.NETWORK}")

    async def spawn_bot(
        self,
        owner_id: int,
        owner_telegram: str,
        bot_name: str,
        bot_token: str,
        personality: str = "ia",
    ) -> Dict[str, Any]:
        """
        Create and start a new bot container.

        Args:
            owner_id: Telegram user ID of the bot owner
            owner_telegram: Telegram username/ID string
            bot_name: Display name for the bot
            bot_token: Telegram bot token (from BotFather)
            personality: Personality ID (default: "ia")

        Returns:
            dict with container_id, name, status, bot_id
        """
        bot_id = str(uuid.uuid4())[:8]
        container_name = f"zero_bot_{bot_id}"

        env = {
            "TELEGRAM_API_ID": os.getenv("TELEGRAM_API_ID", ""),
            "TELEGRAM_API_HASH": os.getenv("TELEGRAM_API_HASH", ""),
            "TELEGRAM_BOT_TOKEN": bot_token,
            "BOT_ID": bot_id,
            "BOT_NAME": bot_name,
            "OWNER_ID": str(owner_id),
            "OWNER_TELEGRAM": owner_telegram,
            "PERSONALITY": personality,
            "REDIS_URL": os.getenv("REDIS_URL", "redis://redis:6379/0"),
            "LANGFLOW_API_URL": os.getenv("LANGFLOW_API_URL", "http://langflow:7860"),
            "CORE_API_URL": os.getenv("CORE_API_URL", "http://core-api:8000"),
            # Without the shared secret the bot's error reports and bug
            # submissions come back 401 and are silently dropped.
            "CORE_API_TOKEN": os.getenv("CORE_API_TOKEN", ""),
            # LLM provider keys — without these the bot has no model to call.
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
            "LLM_MODEL": os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash-0731"),
        }

        try:
            container = self.client.containers.run(
                image=self.BOT_IMAGE,
                name=container_name,
                detach=True,
                environment=env,
                network=self.NETWORK,
                volumes={
                    f"bot_{bot_id}_data": {"bind": "/data", "mode": "rw"},
                },
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "app": "zero-bot",
                    "bot-id": bot_id,
                    "owner-id": str(owner_id),
                    "bot-name": bot_name,
                },
                mem_limit=os.getenv("BOT_MEM_LIMIT", "512m"),
                cpu_period=100000,
                cpu_quota=int(os.getenv("BOT_CPU_QUOTA", "100000")),  # 1 CPU
            )

            logger.info(f"Bot container spawned: {container_name} for owner {owner_id}")

            return {
                "success": True,
                "container_id": container.id,
                "name": container_name,
                "bot_id": bot_id,
                "status": container.status,
                "image": self.BOT_IMAGE,
            }

        except docker.errors.ImageNotFound:
            logger.error(f"Bot image not found: {self.BOT_IMAGE}")
            return {
                "success": False,
                "error": f"Image {self.BOT_IMAGE} not found. Build it first: docker build -t {self.BOT_IMAGE} .",
            }
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def reassign_owner(
        self, bot_id: str, new_owner_id: int, new_owner_telegram: str
    ) -> Dict[str, Any]:
        """
        Recreate a bot container under a new owner.

        A sale only moved ownership in the database; the running container kept
        the previous OWNER_ID in its environment, so the seller stayed admin of
        a bot they no longer owned. The BotFather token lives only in the
        container environment, so it is read back from the old container rather
        than being stored anywhere.
        """
        container_name = f"zero_bot_{bot_id}"
        try:
            old = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            return {"success": False, "error": f"Container {container_name} not found"}

        # Env comes back as ["KEY=value", ...].
        env = {}
        for item in old.attrs.get("Config", {}).get("Env", []) or []:
            key, _, value = item.partition("=")
            env[key] = value

        if not env.get("TELEGRAM_BOT_TOKEN"):
            return {"success": False, "error": "Bot token missing from container env"}

        env["OWNER_ID"] = str(new_owner_id)
        env["OWNER_TELEGRAM"] = new_owner_telegram

        labels = dict(old.labels or {})
        labels["owner-id"] = str(new_owner_id)

        try:
            old.stop(timeout=15)
            old.remove()
            container = self.client.containers.run(
                image=self.BOT_IMAGE,
                name=container_name,
                detach=True,
                environment=env,
                network=self.NETWORK,
                volumes={f"bot_{bot_id}_data": {"bind": "/data", "mode": "rw"}},
                restart_policy={"Name": "unless-stopped"},
                labels=labels,
                mem_limit=os.getenv("BOT_MEM_LIMIT", "512m"),
                cpu_period=100000,
                cpu_quota=int(os.getenv("BOT_CPU_QUOTA", "100000")),
            )
            logger.info(f"Bot {bot_id} reassigned to owner {new_owner_id}")
            return {"success": True, "container_id": container.id}
        except docker.errors.APIError as e:
            logger.error(f"Failed to reassign bot {bot_id}: {e}")
            return {"success": False, "error": str(e)}

    async def stop_bot(self, bot_id: str) -> bool:
        """Stop a bot container (sleep mode)."""
        container_name = f"zero_bot_{bot_id}"
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=30)
            logger.info(f"Bot stopped: {container_name}")
            return True
        except docker.errors.NotFound:
            logger.warning(f"Container not found: {container_name}")
            return False
        except docker.errors.APIError as e:
            logger.error(f"Error stopping bot: {e}")
            return False

    async def start_bot(self, bot_id: str) -> bool:
        """Start a stopped bot container (wake up)."""
        container_name = f"zero_bot_{bot_id}"
        try:
            container = self.client.containers.get(container_name)
            container.start()
            logger.info(f"Bot started: {container_name}")
            return True
        except docker.errors.NotFound:
            logger.warning(f"Container not found: {container_name}")
            return False
        except docker.errors.APIError as e:
            logger.error(f"Error starting bot: {e}")
            return False

    async def restart_bot(self, bot_id: str) -> bool:
        """Restart a bot container (update)."""
        container_name = f"zero_bot_{bot_id}"
        try:
            container = self.client.containers.get(container_name)
            container.restart(timeout=30)
            logger.info(f"Bot restarted: {container_name}")
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError as e:
            logger.error(f"Error restarting bot: {e}")
            return False

    async def destroy_bot(self, bot_id: str) -> bool:
        """Remove a bot container permanently."""
        container_name = f"zero_bot_{bot_id}"
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove(force=True)
            # Remove volume
            try:
                vol = self.client.volumes.get(f"bot_{bot_id}_data")
                vol.remove(force=True)
            except Exception:
                pass
            logger.info(f"Bot destroyed: {container_name}")
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError as e:
            logger.error(f"Error destroying bot: {e}")
            return False

    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Get bot container status."""
        container_name = f"zero_bot_{bot_id}"
        try:
            container = self.client.containers.get(container_name)
            container.reload()
            return {
                "bot_id": bot_id,
                "status": container.status,
                "created": container.attrs["Created"],
                "image": container.attrs["Config"]["Image"],
                "ports": container.attrs["NetworkSettings"]["Ports"],
                "health": container.attrs["State"].get("Health", {}).get("Status", "unknown"),
                "started_at": container.attrs["State"].get("StartedAt", ""),
            }
        except docker.errors.NotFound:
            return {"bot_id": bot_id, "status": "not_found"}
        except docker.errors.APIError as e:
            return {"bot_id": bot_id, "status": "error", "error": str(e)}

    async def list_active_bots(self) -> List[Dict[str, Any]]:
        """List all active bot containers."""
        try:
            containers = self.client.containers.list(
                filters={"label": "app=zero-bot"}
            )
            return [
                {
                    "bot_id": c.labels.get("bot-id"),
                    "owner_id": c.labels.get("owner-id"),
                    "bot_name": c.labels.get("bot-name"),
                    "status": c.status,
                    "name": c.name,
                    "created": c.attrs["Created"],
                }
                for c in containers
            ]
        except docker.errors.APIError as e:
            logger.error(f"Error listing bots: {e}")
            return []

    async def get_bot_logs(self, bot_id: str, tail: int = 100) -> str:
        """Get recent logs from a bot container."""
        container_name = f"zero_bot_{bot_id}"
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode("utf-8", errors="replace")
        except docker.errors.NotFound:
            return f"Container {container_name} not found"
        except docker.errors.APIError as e:
            return f"Error: {e}"

    async def get_platform_stats(self) -> Dict[str, Any]:
        """Get platform-wide container stats."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "app=zero-bot"}
            )
            active = [c for c in containers if c.status == "running"]
            stopped = [c for c in containers if c.status != "running"]

            total_mem = sum(
                c.attrs["HostConfig"].get("Memory", 0)
                for c in active
            )

            return {
                "total_bots": len(containers),
                "active_bots": len(active),
                "stopped_bots": len(stopped),
                "total_memory_mb": total_mem / (1024 * 1024),
                "image": self.BOT_IMAGE,
            }
        except docker.errors.APIError as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
