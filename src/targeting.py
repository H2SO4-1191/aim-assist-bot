import math


def select_target(boxes, model_names, frame_width, frame_height):
    """
    boxes: ultralytics Boxes object (from results[0].boxes)
    model_names: dict like {0: 'player', 1: 'head'}
    Returns: dict with target info, or None if nothing detected.
    """
    center_x, center_y = frame_width / 2, frame_height / 2

    heads = []
    players = []

    for box in boxes:
        cls_id = int(box.cls[0])
        cls_name = model_names.get(cls_id, "")
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        box_center_x = (x1 + x2) / 2
        box_center_y = (y1 + y2) / 2
        distance = math.hypot(box_center_x - center_x, box_center_y - center_y)

        entry = {
            "class": cls_name,
            "center": (box_center_x, box_center_y),
            "distance_to_crosshair": distance,
            "confidence": float(box.conf[0]),
            "bbox": (x1, y1, x2, y2),
        }

        if cls_name == "head":
            heads.append(entry)
        elif cls_name == "player":
            players.append(entry)

    # Prefer heads entirely — only fall back to player boxes if no head detected
    candidates = heads if heads else players
    if not candidates:
        return None

    # Closest to crosshair wins, among whichever class we're using
    best = min(candidates, key=lambda e: e["distance_to_crosshair"])
    best["used_class"] = "head" if heads else "player"
    return best
