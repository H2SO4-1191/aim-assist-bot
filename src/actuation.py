"""
Relative mouse movement via Windows SendInput API.

Why not pydirectinput/pyautogui for this: those move the mouse by setting
absolute cursor position (SetCursorPos under the hood). Most FPS games
read RAW mouse input (hardware deltas) instead of cursor position for
camera control — moving the OS cursor does nothing to the in-game view
in that case. SendInput with MOUSEEVENTF_MOVE sends actual relative
deltas, which raw-input games do respond to.
"""
import ctypes
import time

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


def interpolated_move(dx_total: float, dy_total: float, steps: int = 6, step_delay: float = 0.003):
    """
    Split one movement into several smaller SendInput calls with tiny
    delays between them, instead of one lump move. This is what actually
    fixes the "clunky/robotic" feel — a single big SendInput call per
    detection-frame (~30fps) is visibly stepped; splitting it into several
    smaller moves within that same frame budget approximates continuous
    motion instead.
    """
    if steps <= 0:
        return
    step_dx = dx_total / steps
    step_dy = dy_total / steps
    remainder_x, remainder_y = 0.0, 0.0

    for _ in range(steps):
        # carry sub-pixel remainders forward so small movements don't get
        # truncated to zero every step (int() truncation would otherwise
        # eat fractional pixels and understeer)
        remainder_x += step_dx
        remainder_y += step_dy
        move_x = int(remainder_x)
        move_y = int(remainder_y)
        remainder_x -= move_x
        remainder_y -= move_y
        if move_x != 0 or move_y != 0:
            move_relative(move_x, move_y)
        time.sleep(step_delay)


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
            damped_dx = dx * self.damping_factor  # sign flipped on x — we overshot, brake hard
        if self.last_dy != 0 and (dy > 0) != (self.last_dy > 0):
            damped_dy = dy * self.damping_factor  # same check for y

        self.last_dx, self.last_dy = dx, dy
        return damped_dx, damped_dy


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

    Internally uses interpolated_move to split this into several smaller
    physical mouse moves rather than one lump SendInput call, which is
    what actually makes the motion look smooth instead of stepped.
    """
    dx = dx_total * strength
    dy = dy_total * strength

    # clamp to max_step while preserving direction
    dx = max(-max_step, min(max_step, dx))
    dy = max(-max_step, min(max_step, dy))

    interpolated_move(dx, dy)
