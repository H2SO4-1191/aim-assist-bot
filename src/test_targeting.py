import time
import yaml
import cv2
from ultralytics import YOLO

from capture import ScreenCapture
from targeting import select_target


def load_config(path="../configs/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()
    model = YOLO(cfg["model"]["weights"])
    print(f"Model classes: {model.names}")

    cap = ScreenCapture(region=cfg["capture"]["region"], target_fps=cfg["capture"]["target_fps"])
    print(f"Capture backend: {cap.backend}")

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

            # draw all detections in gray first
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (150, 150, 150), 1)

            # screen center marker (this represents where the crosshair sits)
            cx, cy = w // 2, h // 2
            cv2.drawMarker(annotated, (cx, cy), (255, 255, 255), cv2.MARKER_CROSS, 20, 2)

            target = select_target(boxes, model.names, w, h)
            if target:
                tx, ty = map(int, target["center"])
                x1, y1, x2, y2 = map(int, target["bbox"])
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.line(annotated, (cx, cy), (tx, ty), (0, 255, 0), 2)
                cv2.putText(annotated, f"TARGET: {target['used_class']} "
                           f"(dist: {target['distance_to_crosshair']:.0f}px)",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(annotated, "no target", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("target selection test", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
