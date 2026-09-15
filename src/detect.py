import time
import yaml
import cv2
from pathlib import Path
from ultralytics import YOLO

from capture import ScreenCapture


def load_config(path="../configs/config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()
    model_path = cfg["model"]["weights"]

    if not Path(model_path).exists():
        print(f"[!] {model_path} not found — falling back to yolov8n.pt (COCO) "
              f"for pipeline testing. Train your own model before real use.")
        model_path = "yolov8n.pt"

    model = YOLO(model_path)
    cap = ScreenCapture(region=cfg["capture"]["region"],
                        target_fps=cfg["capture"]["target_fps"])

    print(f"Capture backend: {cap.backend}")
    frame_times = []

    try:
        while True:
            t0 = time.perf_counter()

            frame = cap.get_frame()
            if frame is None:
                continue
            t1 = time.perf_counter()

            results = model.predict(
                frame,
                imgsz=cfg["model"]["imgsz"],
                conf=cfg["model"]["conf_threshold"],
                iou=cfg["model"]["iou_threshold"],
                device=cfg["model"]["device"],
                verbose=False,
            )
            t2 = time.perf_counter()

            annotated = results[0].plot()
            cv2.imshow("aim-assist detection (test view)", annotated)

            capture_ms = (t1 - t0) * 1000
            infer_ms = (t2 - t1) * 1000
            total_ms = (t2 - t0) * 1000
            frame_times.append(total_ms)

            if cfg.get("benchmark"):
                print(f"\rcapture: {capture_ms:5.1f}ms | infer: {infer_ms:5.1f}ms "
                      f"| total: {total_ms:5.1f}ms | ~{1000/total_ms:5.1f} FPS", end="")

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.close()
        cv2.destroyAllWindows()
        if frame_times:
            avg = sum(frame_times) / len(frame_times)
            print(f"\n\nAverage: {avg:.1f}ms/frame -> {1000/avg:.1f} FPS over {len(frame_times)} frames")


if __name__ == "__main__":
    main()
