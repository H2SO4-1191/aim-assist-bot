import ctypes

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
    """Move the mouse by (dx, dy) pixels, relative to current position."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(dx, dy, 0, MOUSEEVENTF_MOVE, 0, ctypes.pointer(extra))
    command = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))


def smoothed_move_toward(dx_total: float, dy_total: float, strength: float, max_step: int = 40):
    """
    Move a FRACTION of the way toward the target this frame, not all at once.
    strength: 0.0-1.0, fraction of the remaining distance to close per call.
    max_step: hard cap on pixels moved in one call, so a sudden huge distance
              (target just appeared) doesn't cause a jarring snap.

    Called once per frame with the CURRENT distance to target — as the
    target gets closer to center, dx_total/dy_total naturally shrink, so
    this produces a decelerating "pull toward" feel rather than constant-
    speed movement or an instant snap.
    """
    dx = dx_total * strength
    dy = dy_total * strength

    # clamp to max_step while preserving direction
    dx = max(-max_step, min(max_step, dx))
    dy = max(-max_step, min(max_step, dy))

    move_relative(int(dx), int(dy))
