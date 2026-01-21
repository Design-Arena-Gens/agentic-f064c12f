from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata
from jarvis.assistant.system.monitor import SystemMonitor


class StatusSkill(Skill):
    metadata = SkillMetadata(
        name="System Status",
        description="Reports CPU usage, memory consumption, and battery level.",
        triggers=("status", "cpu", "memory", "battery", "monitor"),
    )

    def __init__(self) -> None:
        self.monitor = SystemMonitor()

    async def handle(self, text: str, memory: MemoryManager) -> str:
        snapshot = self.monitor.get_snapshot()
        cpu = snapshot.get("cpu")
        ram = snapshot.get("ram")
        battery = snapshot.get("battery")

        response = f"CPU usage is at {cpu:.0f} percent. Memory usage is {ram:.0f} percent."
        if battery is not None:
            response += f" Battery charge stands at {battery:.0f} percent."
        return response
