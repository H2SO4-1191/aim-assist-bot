"""
Screen capture module.

Uses dxcam (Windows Desktop Duplication API) for low-latency capture.
This is the #1 bottleneck in most "real-time CV over games" projects —
mss/PIL-based capture is often 30-80ms per frame, which alone blows your
latency budget. dxcam typically gets this to 2-5ms.

On Linux (no dxcam support), falls back to `mss` automatically so you can
still develop/test the pipeline before moving to the Windows machine
you'll actually run this on for game capture.
"""
import time
import numpy as np

try:
    import dxcam
    _BACKEND = "dxcam"
except ImportError:
    import mss
    _BACKEND = "mss"


class ScreenCapture:
    def __init__(self, region: tuple | None = None, target_fps: int = 60):
        """
        region: (left, top, right, bottom) in screen pixels, or None for full screen.
                Capturing a smaller region centered on the crosshair is one of the
                cheapest wins for latency — you don't need to scan the whole screen
                for enemies far outside your effective aim range anyway.
        """
        self.region = region
        self.backend = _BACKEND

        if self.backend == "dxcam":
            self.camera = dxcam.create(output_idx=0, output_color="BGR")
            self.camera.start(target_fps=target_fps, video_mode=True, region=region)
        else:
            self.sct = mss.mss()
            monitor = self.sct.monitors[1]
            self.region = region or (
                monitor["left"], monitor["top"],
                monitor["left"] + monitor["width"],
                monitor["top"] + monitor["height"],
            )

    def get_frame(self) -> np.ndarray | None:
        """Returns latest frame as BGR numpy array, or None if not ready yet."""
        if self.backend == "dxcam":
            return self.camera.get_latest_frame()
        else:
            left, top, right, bottom = self.region
            shot = self.sct.grab({"left": left, "top": top,
                                   "width": right - left, "height": bottom - top})
            return np.array(shot)[:, :, :3]  # drop alpha channel

    def close(self):
        if self.backend == "dxcam":
            self.camera.stop()


if __name__ == "__main__":
    # Quick benchmark: how many raw frames/sec can we actually pull?
    cap = ScreenCapture()
    print(f"Backend: {cap.backend}")
    n_frames = 200
    t0 = time.time()
    got = 0
    while got < n_frames:
        frame = cap.get_frame()
        if frame is not None:
            got += 1
    elapsed = time.time() - t0
    print(f"Captured {n_frames} frames in {elapsed:.2f}s -> {n_frames/elapsed:.1f} FPS")
    cap.close()
