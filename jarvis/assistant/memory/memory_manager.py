import asyncio
import json
import pathlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from jarvis.utils.logger import get_logger


@dataclass
class UserProfile:
    name: Optional[str] = None
    preferences: Dict[str, str] = field(default_factory=dict)
    custom_commands: Dict[str, str] = field(default_factory=dict)


@dataclass
class MemoryState:
    user: UserProfile = field(default_factory=UserProfile)
    conversation_log: List[Dict[str, str]] = field(default_factory=list)


class MemoryManager:
    """
    Handles persistent memory for Jarvis, stored on disk as JSON.
    """

    def __init__(self, memory_path: pathlib.Path) -> None:
        self.logger = get_logger(__name__)
        self.memory_path = memory_path
        self.state = MemoryState()
        self._lock = asyncio.Lock()

    @property
    def user_profile(self) -> UserProfile:
        return self.state.user

    async def load(self) -> None:
        if not self.memory_path.exists():
            self.logger.info("Memory file not found. Creating a new one at %s", self.memory_path)
            await self.flush()
            return

        self.logger.info("Loading memory from %s", self.memory_path)
        content = await asyncio.get_running_loop().run_in_executor(None, self.memory_path.read_text, "utf-8")
        try:
            data = json.loads(content)
            self.state = MemoryState(
                user=UserProfile(**data.get("user", {})),
                conversation_log=data.get("conversation_log", []),
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.exception("Failed to parse memory file: %s", exc)
            self.state = MemoryState()

    async def flush(self) -> None:
        async with self._lock:
            serialized = json.dumps(asdict(self.state), indent=2)
            await asyncio.get_running_loop().run_in_executor(
                None, self.memory_path.write_text, serialized, "utf-8"
            )
            self.logger.debug("Persisted memory state.")

    async def remember_user_name(self, name: str) -> None:
        self.state.user.name = name
        await self.flush()

    async def set_preference(self, key: str, value: str) -> None:
        self.state.user.preferences[key] = value
        await self.flush()

    async def add_custom_command(self, trigger: str, action: str) -> None:
        self.state.user.custom_commands[trigger.lower()] = action
        await self.flush()

    async def update_from_conversation(self, user_message: str, assistant_message: str) -> None:
        self.state.conversation_log.append({"user": user_message, "assistant": assistant_message})
        max_entries = 50
        if len(self.state.conversation_log) > max_entries:
            self.state.conversation_log = self.state.conversation_log[-max_entries:]
        await self.flush()
