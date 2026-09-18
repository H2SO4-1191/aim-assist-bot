import ctypes
import time
import multiprocessing as mp

# --- ctypes structures matching the Windows SendInput API ---
PUL = ctypes.POINTER(ctypes.c_ulong)

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class Input_I(ctypes.Union):
    _fields_ = [("mi", MouseInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

MOUSEEVENTF_MOVE = 0x0001
INPUT_MOUSE = 0


def move_relative(dx: int, dy: int):
    """Move the mouse by (dx, dy) pixels, relative to current position.
    Works correctly even when called from a different process than the
    main app — SendInput moves the system-wide cursor, it isn't scoped
    to whichever process calls it."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(dx, dy, 0, MOUSEEVENTF_MOVE, 0, ctypes.pointer(extra))
    command = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))


def _request_high_res_timer():
    """Windows' default timer resolution is ~15.6ms — request 1ms instead."""
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass


def _mover_process_main(shared, running_flag, tick_hz: int, duration: float):
    """
    Runs in its own OS process (immune to the main process's GIL).

    KEY CHANGE from the previous version: delivery is now LINEAR over a
    fixed duration, not exponential decay. Exponential decay finishes
    delivering almost the whole correction within the first ~20-30ms and
    then sits idle waiting for the next detection update — that idle gap
    is exactly what reads as separate "chopped steps" rather than one
    continuous motion. Linear delivery spreads the same total movement
    evenly across the whole expected gap between updates instead, so
    it's still smoothly gliding when the next correction arrives.

    Progress is computed from REAL ELAPSED TIME each tick (not an
    assumed step count), so it's self-correcting against any timing
    jitter rather than accumulating drift.

    shared: dict of multiprocessing.Value — target_x, target_y (the
    latest commanded total movement), start_time (when it was issued),
    delivered_x, delivered_y (how much of it has been sent so far).
    """
    _request_high_res_timer()
    tick_interval = 1.0 / tick_hz
    remainder_x, remainder_y = 0.0, 0.0

    while running_flag.value:
        with shared["lock"]:
            target_x = shared["target_x"].value
            target_y = shared["target_y"].value
            start_time = shared["start_time"].value
            delivered_x = shared["delivered_x"].value
            delivered_y = shared["delivered_y"].value

        if target_x != 0 or target_y != 0:
            elapsed = time.perf_counter() - start_time
            fraction = min(1.0, elapsed / duration) if duration > 0 else 1.0

            desired_x = target_x * fraction
            desired_y = target_y * fraction
            send_f_x = desired_x - delivered_x
            send_f_y = desired_y - delivered_y

            remainder_x += send_f_x
            remainder_y += send_f_y
            send_x = int(remainder_x)
            send_y = int(remainder_y)
            remainder_x -= send_x
            remainder_y -= send_y

            if send_x != 0 or send_y != 0:
                move_relative(send_x, send_y)

            with shared["lock"]:
                # only advance delivered-so-far if nothing newer arrived
                # while we were computing (avoid clobbering a fresh target)
                if shared["start_time"].value == start_time:
                    shared["delivered_x"].value = delivered_x + send_f_x
                    shared["delivered_y"].value = delivered_y + send_f_y

        time.sleep(tick_interval)


class MouseSmootherProcess:
    def __init__(self, tick_hz: int = 250, duration: float = 0.12):
        """
        duration: how long ONE correction's linear glide should take.
        Tuned to roughly match the typical gap between detection updates
        so the motion is still gliding (not idle) when fresh data arrives.
        120ms is a starting point — raise it if motion still looks like
        separate steps (detection updates are arriving slower than this),
        lower it if it starts feeling laggy/behind (updates are faster
        than this and the glide is now the bottleneck).
        """
        self._lock = mp.Lock()
        self._shared = {
            "lock": self._lock,
            "target_x": mp.Value('d', 0.0, lock=False),
            "target_y": mp.Value('d', 0.0, lock=False),
            "start_time": mp.Value('d', time.perf_counter(), lock=False),
            "delivered_x": mp.Value('d', 0.0, lock=False),
            "delivered_y": mp.Value('d', 0.0, lock=False),
        }
        self._running = mp.Value('b', 1)
        self._process = mp.Process(
            target=_mover_process_main,
            args=(self._shared, self._running, tick_hz, duration),
            daemon=True,
        )
        self._process.start()

    def queue_move(self, dx: float, dy: float):
        with self._lock:
            self._shared["target_x"].value = dx
            self._shared["target_y"].value = dy
            self._shared["start_time"].value = time.perf_counter()
            self._shared["delivered_x"].value = 0.0
            self._shared["delivered_y"].value = 0.0

    def stop(self):
        self._running.value = 0


_smoother = None

def _get_smoother():
    global _smoother
    if _smoother is None:
        _smoother = MouseSmootherProcess()
    return _smoother


class OvershootDamper:
    """
    Fixes oscillation (moving fast, overshooting the target, correcting
    back the other way, repeat) — a classic symptom of proportional gain
    being too high for an UNKNOWN game sensitivity setting. We can't know
    how many degrees of camera rotation one pixel of mouse movement causes
    in any given game, so at higher strength values the correction can
    easily overshoot past the target every frame.

    Fix: track the error direction (dx sign) frame to frame. If it flips
    sign, that means we just crossed over the target — heavily damp this
    frame's correction so we don't immediately overshoot back the other
    way. This breaks the oscillation loop instead of just hiding it.
    """
    def __init__(self, damping_factor: float = 0.25):
        self.damping_factor = damping_factor
        self.last_dx = 0.0
        self.last_dy = 0.0

    def apply(self, dx: float, dy: float):
        damped_dx = dx
        damped_dy = dy

        if self.last_dx != 0 and (dx > 0) != (self.last_dx > 0):
            damped_dx = dx * self.damping_factor
        if self.last_dy != 0 and (dy > 0) != (self.last_dy > 0):
            damped_dy = dy * self.damping_factor

        self.last_dx, self.last_dy = dx, dy
        return damped_dx, damped_dy


def smoothed_move_toward(dx_total: float, dy_total: float, strength: float, max_step: int = 40):
    """
    Same public interface as before — strength/clamping math unchanged.
    Delivery now glides linearly to the target over a fixed duration in
    a separate process, instead of exponentially decaying in a thread.
    """
    dx = dx_total * strength
    dy = dy_total * strength

    dx = max(-max_step, min(max_step, dx))
    dy = max(-max_step, min(max_step, dy))

    _get_smoother().queue_move(dx, dy)
