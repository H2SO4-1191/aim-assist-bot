"""
Shared state between the UI thread and the detection/actuation thread.
A simple lock-protected container — avoids the two threads stepping on
each other when the UI writes a new strength value while the detection
loop is mid-read.
"""
import threading

class SharedState:
    def __init__(self):
        self._lock = threading.Lock()
        self.enabled = False
        self.ads_only = False
        self.strength = 0.15
        self.running = True  # set False to signal both threads to stop

    def get_snapshot(self):
        with self._lock:
            return {
                "enabled": self.enabled,
                "ads_only": self.ads_only,
                "strength": self.strength,
                "running": self.running,
            }

    def set_enabled(self, value: bool):
        with self._lock:
            self.enabled = value

    def set_ads_only(self, value: bool):
        with self._lock:
            self.ads_only = value

    def set_strength(self, value: float):
        with self._lock:
            self.strength = value

    def stop(self):
        with self._lock:
            self.running = False
