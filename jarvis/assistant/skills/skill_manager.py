import asyncio
import importlib
import inspect
import pkgutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill
from jarvis.utils.logger import get_logger


class SkillManager:
    """
    Loads, manages, and executes Jarvis skills.
    """

    def __init__(self, memory_manager: MemoryManager):
        self.logger = get_logger(__name__)
        self.memory = memory_manager
        self.skills: List[Skill] = []
        self.skill_directory = Path(__file__).parent / "builtin"
        self.custom_skill_directory = Path(__file__).parent / "custom"
        self.custom_skill_directory.mkdir(exist_ok=True, parents=True)

    async def load_builtin_skills(self) -> None:
        self.logger.info("Loading builtin skills from %s", self.skill_directory)
        self.skills = []
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_skills_from_package, "jarvis.assistant.skills.builtin")
        await loop.run_in_executor(None, self._load_skills_from_package, "jarvis.assistant.skills.custom")

    def _load_skills_from_package(self, package_name: str) -> None:
        importlib.invalidate_caches()
        package = importlib.import_module(package_name)
        for module_info in pkgutil.iter_modules(package.__path__):
            module_name = f"{package_name}.{module_info.name}"
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Skill) and obj is not Skill:
                    self._register_skill(obj())

    def _register_skill(self, skill: Skill) -> None:
        if hasattr(skill, "set_skill_manager"):
            skill.set_skill_manager(self)  # type: ignore[attr-defined]
        self.logger.debug("Registered skill %s", skill.metadata.name)
        self.skills.append(skill)

    async def execute(self, text: str) -> Optional[str]:
        for skill in self.skills:
            try:
                if await skill.can_handle(text):
                    self.logger.info("Dispatching to skill %s", skill.metadata.name)
                    return await skill.handle(text, self.memory)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.logger.exception("Skill %s failed: %s", skill.metadata.name, exc)
        return "I'm afraid I can't comply with that request just yet."
