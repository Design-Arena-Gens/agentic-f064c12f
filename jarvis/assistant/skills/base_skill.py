from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.assistant.memory.memory_manager import MemoryManager


@dataclass
class SkillMetadata:
    name: str
    description: str
    triggers: tuple[str, ...]


class Skill:
    metadata: SkillMetadata

    async def can_handle(self, text: str) -> bool:
        lowered = text.lower()
        return any(lowered.startswith(trigger) for trigger in self.metadata.triggers)

    async def handle(self, text: str, memory: "MemoryManager") -> str:
        raise NotImplementedError
