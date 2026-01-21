import argparse
import asyncio
import signal

from jarvis.assistant.core import JarvisAssistant
from jarvis.gui.tray_app import TrayApplication
from jarvis.utils.logger import configure_logging


async def run(check_only: bool = False) -> None:
    configure_logging()

    assistant = JarvisAssistant()
    tray = TrayApplication(assistant=assistant)

    loop = asyncio.get_running_loop()

    stop_event = asyncio.Event()

    def _handle_shutdown(*_args):
        loop.create_task(_shutdown())

    async def _shutdown():
        if not stop_event.is_set():
            stop_event.set()
            await assistant.shutdown()
            tray.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_shutdown)

    try:
        if check_only:
            await assistant.memory.load()
            await assistant.skill_manager.load_builtin_skills()
            await assistant.llm.generate_response(
                prompt="Run a quick systems diagnostic summary.",
                system_prompt="You are Jarvis performing a startup check.",
            )
            await assistant.synthesizer.speak("Diagnostics complete. All subsystems nominal.")
            await assistant.shutdown()
            return

        await assistant.start()
        tray.start()
        await stop_event.wait()
    finally:
        await assistant.shutdown()
        tray.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch the Jarvis assistant.")
    parser.add_argument("--check", action="store_true", help="Run a diagnostics check and exit.")
    args = parser.parse_args()
    asyncio.run(run(check_only=args.check))
