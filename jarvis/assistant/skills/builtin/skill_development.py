import json
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata
from jarvis.utils.logger import get_logger

if TYPE_CHECKING:
    from jarvis.assistant.skills.skill_manager import SkillManager


class SkillDevelopmentSkill(Skill):
    metadata = SkillMetadata(
        name="Skill Development",
        description="Guides Jarvis through creating, updating, and rolling back modular skills.",
        triggers=("create skill", "improve skill", "rollback skill", "confirm skill", "cancel skill"),
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.skill_manager: Optional["SkillManager"] = None
        self.pending_key = "pending_skill_change"

    def set_skill_manager(self, manager: SkillManager) -> None:
        self.skill_manager = manager

    async def handle(self, text: str, memory: MemoryManager) -> str:
        lowered = text.lower()
        if lowered.startswith("create skill"):
            return await self._prepare_creation(text, memory)
        if lowered.startswith("improve skill"):
            return await self._prepare_update(text, memory)
        if lowered.startswith("rollback skill"):
            return await self._rollback_skill(text, memory)
        if lowered.startswith("confirm skill"):
            return await self._commit_pending(memory)
        if lowered.startswith("cancel skill"):
            memory.state.user.preferences.pop(self.pending_key, None)
            await memory.flush()
            return "Pending skill changes have been cancelled."
        return "I didn't recognise that instruction in the skill workshop."

    async def _prepare_creation(self, text: str, memory: MemoryManager) -> str:
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return "Please specify the skill name and purpose, for example 'create skill Stretch Coach: reminds me to stretch'."
        payload = parts[2]
        if ":" in payload:
            name, description = [segment.strip() for segment in payload.split(":", 1)]
        else:
            tokens = payload.split(" ", 1)
            name = tokens[0]
            description = tokens[1] if len(tokens) > 1 else "Custom Jarvis skill."

        pending = {
            "action": "create",
            "name": name,
            "description": description,
            "triggers": tuple(word.strip().lower() for word in name.split()),
        }
        memory.state.user.preferences[self.pending_key] = json.dumps(pending)
        await memory.flush()
        return (
            f"Blueprint ready for skill '{name}'. "
            "Say 'confirm skill changes' when you're happy, or 'cancel skill changes' to abort."
        )

    async def _prepare_update(self, text: str, memory: MemoryManager) -> str:
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return "Please specify which skill to improve, e.g. 'improve skill status: add temperatures'."
        payload = parts[2]
        if ":" in payload:
            name, instructions = [segment.strip() for segment in payload.split(":", 1)]
        else:
            name, instructions = payload, "No additional guidance supplied."

        pending = {
            "action": "update",
            "name": name,
            "instructions": instructions,
        }
        memory.state.user.preferences[self.pending_key] = json.dumps(pending)
        await memory.flush()
        return (
            f"Update plan drafted for '{name}'. "
            "Please review and say 'confirm skill changes' to proceed or 'cancel skill changes' to stop."
        )

    async def _rollback_skill(self, text: str, memory: MemoryManager) -> str:
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return "Please specify the skill to roll back, for example 'rollback skill stretch'."
        if not self.skill_manager:
            return "Skill management subsystems aren't ready for rollbacks yet."
        name = parts[2].strip().lower()
        history = json.loads(memory.state.user.preferences.get("skill_history", "{}"))
        archive_path = history.get(name)
        if not archive_path or not Path(archive_path).exists():
            return "I can't find an archived version of that skill."
        target = self._skill_path(name)
        Path(target).write_text(Path(archive_path).read_text(encoding="utf-8"), encoding="utf-8")
        if self.skill_manager:
            await self.skill_manager.load_builtin_skills()
        return f"The skill '{name}' has been restored from backup."

    async def _commit_pending(self, memory: MemoryManager) -> str:
        pending_json = memory.state.user.preferences.get(self.pending_key)
        if not pending_json:
            return "There's no skill work awaiting confirmation."
        pending = json.loads(pending_json)
        action = pending.get("action")
        if action == "create":
            message = await self._create_skill(pending, memory)
        elif action == "update":
            message = await self._update_skill(pending, memory)
        else:
            message = "I couldn't identify the pending skill action."
        memory.state.user.preferences.pop(self.pending_key, None)
        await memory.flush()
        if self.skill_manager:
            await self.skill_manager.load_builtin_skills()
        return message

    async def _create_skill(self, payload: dict, memory: MemoryManager) -> str:
        if not self.skill_manager:
            return "Skill management isn't initialised, so I can't write code just yet."
        name = payload["name"]
        triggers = payload.get("triggers", (name.lower(),))
        description = payload.get("description", "Custom Jarvis skill.")
        slug = "_".join(name.lower().split())
        path = self._skill_path(slug)
        if path.exists():
            backup = path.with_suffix(".bak")
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        template = self._skill_template(name, description, triggers)
        path.write_text(template, encoding="utf-8")
        return f"The skill '{name}' is live. I've routed it through the custom skill loader."

    async def _update_skill(self, payload: dict, memory: MemoryManager) -> str:
        if not self.skill_manager:
            return "Skill management isn't initialised, so I can't update skills right now."
        name = payload["name"]
        instructions = payload.get("instructions", "")
        slug = "_".join(name.lower().split())
        path = self._skill_path(slug)
        if not path.exists():
            return "I couldn't locate that skill for updating."
        backup = path.with_suffix(".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        history = json.loads(memory.state.user.preferences.get("skill_history", "{}"))
        history[slug] = str(backup)
        memory.state.user.preferences["skill_history"] = json.dumps(history)
        await memory.flush()
        augmented = path.read_text(encoding="utf-8") + f"\n# Pending instructions: {instructions}\n"
        path.write_text(augmented, encoding="utf-8")
        return f"I've appended guidance to '{name}'. Please apply the code changes manually and reload when ready."

    def _skill_template(self, name: str, description: str, triggers: tuple[str, ...]) -> str:
        trigger_repr = ", ".join(f"'{trigger}'" for trigger in triggers)
        class_name = "".join(word.capitalize() for word in name.split())
        return f"""from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata


class {class_name}Skill(Skill):
    metadata = SkillMetadata(
        name="{name}",
        description="{description}",
        triggers=({trigger_repr},),
    )

    async def handle(self, text: str, memory: MemoryManager) -> str:
        return "This is a freshly minted skill. Please customise its behaviour, sir."
"""

    def _skill_path(self, slug: str) -> Path:
        if not self.skill_manager:
            raise RuntimeError("Skill manager not attached.")
        return self.skill_manager.custom_skill_directory / f"{slug}.py"
