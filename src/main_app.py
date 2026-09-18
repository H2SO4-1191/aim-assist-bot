import threading
import yaml
import cv2
import keyboard
from ultralytics import YOLO

from capture import ScreenCapture
from targeting import select_target
from actuation import smoothed_move_toward
from input_state import is_ads_held
from shared_state import SharedState
from control_ui import launch_ui

MAX_STEP_PIXELS = 40
DEADZONE_PIXELS = 8
STRENGTH_STEP = 0.05
STRENGTH_MIN, STRENGTH_MAX = 0.05, 0.6


def load_config(path="../configs/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def detection_loop(state: SharedState):
    cfg = load_config()
    model = YOLO(cfg["model"]["weights"])
    print(f"Model classes: {model.names}")

    cap = ScreenCapture(region=cfg["capture"]["region"], target_fps=cfg["capture"]["target_fps"])
    print(f"Capture backend: {cap.backend}")

    show_window = {"value": True}  # mutable so the F5 hotkey closure can flip it
    keyboard.add_hotkey("f5", lambda: toggle_debug_window(show_window))

    try:
        while True:
            snapshot = state.get_snapshot()
            if not snapshot["running"]:
                break

            frame = cap.get_frame()
            if frame is None:
                continue

            h, w = frame.shape[:2]
            results = model.predict(
                frame, imgsz=cfg["model"]["imgsz"],
                conf=cfg["model"]["conf_threshold"],
                iou=cfg["model"]["iou_threshold"],
                device=cfg["model"]["device"], verbose=False,
            )
            boxes = results[0].boxes

            cx, cy = w // 2, h // 2
            target = select_target(boxes, model.names, w, h)

            should_act = snapshot["enabled"]
            if snapshot["ads_only"]:
                should_act = should_act and is_ads_held()

            if target and should_act:
                tx, ty = target["center"]
                dx, dy = tx - cx, ty - cy
                if target["distance_to_crosshair"] > DEADZONE_PIXELS:
                    smoothed_move_toward(dx, dy, snapshot["strength"], MAX_STEP_PIXELS)

            if show_window["value"]:
                annotated = frame.copy()
                status_text = "ENABLED" if snapshot["enabled"] else "DISABLED"
                if snapshot["enabled"] and snapshot["ads_only"] and not is_ads_held():
                    status_text += " (waiting for ADS)"
                color = (0, 255, 0) if snapshot["enabled"] else (0, 0, 255)
                cv2.putText(annotated, f"{status_text} | strength={snapshot['strength']:.2f} "
                           f"| ads_only={snapshot['ads_only']} (F5 hides this window)",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                if target:
                    x1, y1, x2, y2 = map(int, target["bbox"])
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.imshow("aim assist", annotated)
            else:
                # window was just hidden this frame — destroy it so it actually disappears
                cv2.destroyWindow("aim assist") if cv2.getWindowProperty(
                    "aim assist", cv2.WND_PROP_VISIBLE) >= 1 else None

            if cv2.waitKey(1) & 0xFF == ord("q"):
                state.stop()
                break
    finally:
        cap.close()
        cv2.destroyAllWindows()


def toggle_debug_window(show_window: dict):
    show_window["value"] = not show_window["value"]
    print(f"\n[Debug window {'SHOWN' if show_window['value'] else 'HIDDEN'}]")


def main():
    state = SharedState()

    keyboard.add_hotkey("f1", lambda: state.set_enabled(not state.enabled))
    keyboard.add_hotkey("f2", lambda: state.set_ads_only(not state.ads_only))
    keyboard.add_hotkey("f3", lambda: state.set_strength(
        max(STRENGTH_MIN, round(state.strength - STRENGTH_STEP, 2))))
    keyboard.add_hotkey("f4", lambda: state.set_strength(
        min(STRENGTH_MAX, round(state.strength + STRENGTH_STEP, 2))))

    print("F1: toggle enable | F2: toggle ADS-only | F3/F4: strength -/+ | F5: toggle debug window")

    detection_thread = threading.Thread(target=detection_loop, args=(state,), daemon=True)
    detection_thread.start()

    launch_ui(state)  # blocks in main thread until UI window closes

    state.stop()
    keyboard.remove_all_hotkeys()


if __name__ == "__main__":
    main()