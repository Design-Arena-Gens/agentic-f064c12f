import asyncio
from typing import Optional

import httpx

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.utils.logger import get_logger


class LLMClient:
    """
    Interfaces with a locally hosted Ollama model (e.g., phi3, llama3).
    """

    def __init__(self, memory_manager: MemoryManager, model: str = "phi3:mini") -> None:
        self.logger = get_logger(__name__)
        self.model = model
        self.memory = memory_manager
        self.client = httpx.AsyncClient(
            base_url="http://localhost:11434",
            timeout=httpx.Timeout(60.0, read=120.0),
        )

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        conversation_context = self._build_conversation_context()
        payload = {
            "model": self.model,
            "prompt": self._compose_prompt(system_prompt, conversation_context, prompt),
            "stream": False,
        }

        self.logger.debug("Sending prompt to Ollama model %s", self.model)
        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        content = response.json()
        return content.get("response", "").strip()

    def _build_conversation_context(self) -> str:
        messages = self.memory.state.conversation_log[-6:]
        formatted = []
        for message in messages:
            formatted.append(f"User: {message['user']}")
            formatted.append(f"Jarvis: {message['assistant']}")
        return "\n".join(formatted)

    @staticmethod
    def _compose_prompt(system_prompt: Optional[str], conversation: str, latest: str) -> str:
        sections = []
        if system_prompt:
            sections.append(f"System:\n{system_prompt}")
        if conversation:
            sections.append(f"Recent conversation:\n{conversation}")
        sections.append(f"User: {latest}")
        sections.append("Jarvis:")
        return "\n\n".join(sections)

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
