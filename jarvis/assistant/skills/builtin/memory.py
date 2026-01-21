from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata


class MemorySkill(Skill):
    metadata = SkillMetadata(
        name="Memory Management",
        description="Learns user details such as name and preferences.",
        triggers=("my name is", "remember", "set preference", "serious mode", "casual mode"),
    )

    async def handle(self, text: str, memory: MemoryManager) -> str:
        lowered = text.lower()
        if lowered.startswith("my name is"):
            name = text[len("my name is") :].strip().split()[0]
            await memory.remember_user_name(name)
            return f"Understood. I'll remember that your name is {name}."

        if lowered.startswith("remember"):
            remainder = text[len("remember") :].strip()
            if " is " in remainder:
                key, value = remainder.split(" is ", 1)
                await memory.set_preference(key.strip(), value.strip())
                return f"I'll remember that {key.strip()} is {value.strip()}."
            return "Could you rephrase that memory in the format 'remember coffee is black'?"

        if lowered.startswith("set preference"):
            parts = lowered.split(" ")
            if len(parts) >= 4:
                key = parts[2]
                value = " ".join(parts[3:])
                await memory.set_preference(key, value)
                return f"Preference updated: {key} is now {value}."

        if "serious mode" in lowered:
            await memory.set_preference("tone", "serious")
            return "Switching to a more serious tone."

        if "casual mode" in lowered:
            await memory.set_preference("tone", "casual")
            return "Back to my usual charming self."

        return "I'm not sure how to store that memory just yet."
