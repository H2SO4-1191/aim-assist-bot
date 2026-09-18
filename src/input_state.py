import ctypes

VK_RBUTTON = 0x02  # right mouse button — the default ADS key in most FPS games


def is_ads_held(vk_code: int = VK_RBUTTON) -> bool:
    """Returns True if the given virtual key is currently pressed."""
    # high-order bit set = currently pressed
    state = ctypes.windll.user32.GetAsyncKeyState(vk_code)
    return bool(state & 0x8000)
