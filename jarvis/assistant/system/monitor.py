import psutil

from jarvis.utils.logger import get_logger


class SystemMonitor:
    """
    Samples CPU, RAM, and battery metrics for quick diagnostics.
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.last_sample = {}

    def sample(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        battery = None
        if hasattr(psutil, "sensors_battery"):
            battery_info = psutil.sensors_battery()
            battery = battery_info.percent if battery_info else None

        self.last_sample = {"cpu": cpu, "ram": ram, "battery": battery}
        self.logger.debug("Sampled system metrics: %s", self.last_sample)

    def get_snapshot(self) -> dict:
        if not self.last_sample:
            self.sample()
        return self.last_sample.copy()
