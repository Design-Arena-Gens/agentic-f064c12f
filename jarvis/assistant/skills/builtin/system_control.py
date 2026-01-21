import asyncio
import os
import subprocess
from pathlib import Path

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata
from jarvis.utils.logger import get_logger


class SystemControlSkill(Skill):
    metadata = SkillMetadata(
        name="System Control",
        description="Opens and closes whitelisted desktop applications and folders.",
        triggers=("open", "launch", "close", "shutdown", "restart"),
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.launch_whitelist = {
            "notepad": r"C:\Windows\System32\notepad.exe",
            "calculator": r"C:\Windows\System32\calc.exe",
            "command prompt": r"C:\Windows\System32\cmd.exe",
            "explorer": r"C:\Windows\explorer.exe",
            "visual studio code": str(Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe"),
        }
        self.folder_whitelist = {
            "documents": str(Path.home() / "Documents"),
            "downloads": str(Path.home() / "Downloads"),
            "pictures": str(Path.home() / "Pictures"),
        }

    async def handle(self, text: str, memory: MemoryManager) -> str:
        lowered = text.lower()

        if lowered.startswith(("shutdown", "restart")):
            action = "shutdown" if "shutdown" in lowered else "restart"
            memory.state.user.preferences["pending_action"] = action
            await memory.flush()
            return (
                f"A {action} is a serious step. Please confirm by saying 'Jarvis confirm {action}' "
                "or cancel by saying 'Jarvis cancel action'."
            )

        if lowered.startswith("open folder"):
            return await self._open_folder(lowered)

        if lowered.startswith(("open", "launch")):
            return await self._launch_application(lowered)

        if lowered.startswith("close"):
            return await self._close_application(lowered)

        return "That command isn't mapped yet, sir."

    async def _launch_application(self, text: str) -> str:
        for friendly, path in self.launch_whitelist.items():
            if friendly in text:
                if not Path(path).exists():
                    return f"I cannot find {friendly} at the expected location."
                self.logger.info("Launching %s (%s)", friendly, path)
                await asyncio.get_running_loop().run_in_executor(None, subprocess.Popen, [path])
                return f"Launching {friendly} now."
        return "I'm afraid that application isn't on my approved list."

    async def _close_application(self, text: str) -> str:
        for friendly, path in self.launch_whitelist.items():
            exe_name = Path(path).name
            if friendly in text:
                self.logger.info("Closing %s via taskkill", exe_name)
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    subprocess.run,
                    ["taskkill", "/IM", exe_name, "/F"],
                    {"check": False, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE},
                )
                return f"I've attempted to close {friendly}."
        return "I don't have clearance to close that application."

    async def _open_folder(self, text: str) -> str:
        for friendly, path in self.folder_whitelist.items():
            if friendly in text:
                if not Path(path).exists():
                    return f"The {friendly} directory is missing."
                self.logger.info("Opening folder %s", path)
                await asyncio.get_running_loop().run_in_executor(None, os.startfile, path)
                return f"Opening your {friendly}."
        return "That folder isn't in my directory whitelist, sorry."
