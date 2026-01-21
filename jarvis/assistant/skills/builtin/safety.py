import asyncio
import subprocess

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata
from jarvis.utils.logger import get_logger


class SafetyConfirmationSkill(Skill):
    metadata = SkillMetadata(
        name="Safety Confirmation",
        description="Handles confirmations for sensitive system actions.",
        triggers=("jarvis confirm", "confirm", "jarvis cancel", "cancel"),
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    async def handle(self, text: str, memory: MemoryManager) -> str:
        lowered = text.lower()
        pending = memory.state.user.preferences.get("pending_action")
        if not pending:
            return "There's nothing awaiting confirmation, sir."

        if "cancel" in lowered:
            memory.state.user.preferences.pop("pending_action", None)
            await memory.flush()
            return "Understood. I've cancelled the pending action."

        if "confirm" in lowered:
            if pending == "shutdown":
                return await self._execute_system(memory, ["shutdown", "/s", "/f", "/t", "5"], "Shutting down in five seconds.")
            if pending == "restart":
                return await self._execute_system(memory, ["shutdown", "/r", "/f", "/t", "5"], "Restarting in five seconds.")
        return "The requested confirmation doesn't match the pending action."

    async def _execute_system(self, memory: MemoryManager, cmd: list[str], success_message: str) -> str:
        memory.state.user.preferences.pop("pending_action", None)
        await memory.flush()
        self.logger.warning("Executing sensitive command: %s", cmd)
        await asyncio.get_running_loop().run_in_executor(
            None,
            subprocess.run,
            cmd,
            {"check": False, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE},
        )
        return success_message
