from ultralytics import YOLO

def main():
    model = YOLO("yolov8n.pt")  # start from COCO-pretrained weights, not random init

    results = model.train(
        data="../data/stage1_final/data.yaml",
        epochs=50,
        imgsz=640,
        batch=16,           # drop to 8 if you hit CUDA out-of-memory on 8GB VRAM
        device=0,           # GPU 0 (RTX 3070)
        patience=15,        # stop early if val mAP doesn't improve for 15 epochs
        project="../models/runs",
        name="stage1_player_detector",
        pretrained=True,
        verbose=True,
    )

    print("\nTraining complete.")

if __name__ == "__main__":
    main()
