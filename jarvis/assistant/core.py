import asyncio
import pathlib
from typing import Optional

from jarvis.assistant.llm.llm_client import LLMClient
from jarvis.assistant.memory.memory_manager import MemoryManager, UserProfile
from jarvis.assistant.skills.skill_manager import SkillManager
from jarvis.assistant.speech.speech_listener import SpeechListener
from jarvis.assistant.speech.speech_synthesizer import SpeechSynthesizer
from jarvis.assistant.system.monitor import SystemMonitor
from jarvis.utils.logger import get_logger


class JarvisAssistant:
    """
    Coordinates the major subsystems that power the Jarvis experience.
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        base_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        data_dir = base_dir / "jarvis" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        self.memory = MemoryManager(memory_path=data_dir / "memory.json")
        self.skill_manager = SkillManager(memory_manager=self.memory)
        self.llm = LLMClient(memory_manager=self.memory)
        self.synthesizer = SpeechSynthesizer()
        self.listener = SpeechListener(memory_manager=self.memory)
        self.monitor = SystemMonitor()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._speech_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        self.logger.info("Starting Jarvis subsystems")
        self._loop = asyncio.get_running_loop()
        await self.memory.load()
        await self.skill_manager.load_builtin_skills()
        self.listener.configure_wake_word()
        self.listener.attach_loop(self._loop)

        self._speech_task = self._loop.create_task(self._speech_loop(), name="jarvis-speech-loop")
        self._monitor_task = self._loop.create_task(self._monitor_loop(), name="jarvis-monitor-loop")
        self._running = True

    async def shutdown(self) -> None:
        if not self._running:
            return

        self.logger.info("Shutting down Jarvis")
        tasks = [task for task in (self._speech_task, self._monitor_task) if task]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        await self.synthesizer.shutdown()
        await self.llm.close()
        await self.memory.flush()
        self._running = False

    async def _speech_loop(self) -> None:
        while True:
            try:
                transcription = await self.listener.listen()
                if transcription is None:
                    continue

                if transcription.intent == "command":
                    await self._handle_command(transcription.text)
                else:
                    await self._handle_conversation(transcription.text)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.logger.exception("Error in speech loop: %s", exc)
                await asyncio.sleep(1.0)

    async def _monitor_loop(self) -> None:
        while True:
            try:
                self.monitor.sample()
                await asyncio.sleep(30.0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.logger.exception("Error in monitor loop: %s", exc)
                await asyncio.sleep(5.0)

    async def _handle_conversation(self, text: str) -> None:
        self.logger.debug("Handling conversational input: %s", text)
        user_profile: UserProfile = self.memory.user_profile
        system_prompt = self._build_system_prompt(user_profile)
        response = await self.llm.generate_response(prompt=text, system_prompt=system_prompt)
        await self.memory.update_from_conversation(user_message=text, assistant_message=response)
        await self.synthesizer.speak(response)

    async def _handle_command(self, text: str) -> None:
        self.logger.debug("Handling command: %s", text)
        command_response = await self.skill_manager.execute(text)
        if command_response:
            await self.synthesizer.speak(command_response)

    @staticmethod
    def _build_system_prompt(profile: UserProfile) -> str:
        persona = (
            "You are Jarvis, a sophisticated AI assistant inspired by Tony Stark's AI. "
            "You are witty, polite, slightly sarcastic, and extremely competent. "
            "You adapt to the user's preferences, remain professional during system operations, "
            "and shift to a more serious tone when explicitly requested. "
            "Keep responses concise, clear, and useful while maintaining warmth."
        )
        memory_bits = []
        if profile.name:
            memory_bits.append(f"The user's name is {profile.name}.")
        if profile.preferences:
            pref_summary = "; ".join(f"{k}: {v}" for k, v in profile.preferences.items())
            memory_bits.append(f"User preferences: {pref_summary}")
        memory_context = " ".join(memory_bits)
        return f"{persona} {memory_context}"
