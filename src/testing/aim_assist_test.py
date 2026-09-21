
import yaml
import cv2
import keyboard
from ultralytics import YOLO

from capture import ScreenCapture
from targeting import select_target
from actuation import smoothed_move_toward

STRENGTH = 0.15       # fraction of remaining distance closed per frame
MAX_STEP_PIXELS = 40  # hard cap per-frame movement, prevents jarring snaps
DEADZONE_PIXELS = 8   # if target is already this close to center, don't micro-jitter

enabled = False


def toggle_enabled():
    global enabled
    enabled = not enabled
    print(f"\n[Aim assist {'ENABLED' if enabled else 'DISABLED'}]")


def load_config(path="../configs/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()
    model = YOLO(cfg["model"]["weights"])
    keyboard.add_hotkey("f1", toggle_enabled)
    print("Press F1 to toggle aim assist. Starting DISABLED.")
    print(f"Strength: {STRENGTH} | Max step: {MAX_STEP_PIXELS}px | Deadzone: {DEADZONE_PIXELS}px")

    cap = ScreenCapture(region=cfg["capture"]["region"], target_fps=cfg["capture"]["target_fps"])

    try:
        while True:
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
            annotated = frame.copy()

            cx, cy = w // 2, h // 2
            target = select_target(boxes, model.names, w, h)

            status_color = (0, 255, 0) if enabled else (0, 0, 255)
            cv2.putText(annotated, f"{'ENABLED' if enabled else 'DISABLED'} (F1 to toggle)",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

            if target:
                tx, ty = target["center"]
                dx, dy = tx - cx, ty - cy
                distance = target["distance_to_crosshair"]

                x1, y1, x2, y2 = map(int, target["bbox"])
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

                if enabled and distance > DEADZONE_PIXELS:
                    smoothed_move_toward(dx, dy, STRENGTH, MAX_STEP_PIXELS)

            cv2.imshow("aim assist test", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.close()
        cv2.destroyAllWindows()
        keyboard.remove_all_hotkeys()


if __name__ == "__main__":
    main()
