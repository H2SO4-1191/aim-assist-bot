import math
import time
from targeting import select_target


class StickyTargetTracker:
    def __init__(self, match_radius: float = 200.0, lost_timeout: float = 0.4,
                 engage_radius_fraction: float = 0.15):
        """
        match_radius: how far (in pixels) a new detection can be from the
                      locked target's last known position and still count
                      as "the same target."
        lost_timeout: how long (seconds) to tolerate the locked target not
                      being found before giving up and picking a new one.
        engage_radius_fraction: fraction of the frame's diagonal within
                      which a NEW target can be acquired — stops the
                      assist from jumping across a crowded screen to
                      whoever is technically "closest" out of everyone
                      visible, however far away that still is.
        """
        self.match_radius = match_radius
        self.lost_timeout = lost_timeout
        self.engage_radius_fraction = engage_radius_fraction
        self.locked_center = None
        self.last_seen_time = 0

    def update(self, boxes, model_names, frame_width, frame_height):
        engage_radius = self.engage_radius_fraction * math.hypot(frame_width, frame_height)
        all_target = select_target(boxes, model_names, frame_width, frame_height,
                                   max_distance=engage_radius)

        if self.locked_center is not None:
            candidates = self._all_candidates(boxes, model_names, frame_width, frame_height)
            match = self._find_closest(candidates, self.locked_center)

            if match and match["distance_to_lock"] <= self.match_radius:
                self.locked_center = match["center"]
                self.last_seen_time = time.time()
                return match["entry"]

            if time.time() - self.last_seen_time < self.lost_timeout:
                return None  # briefly missing (occlusion/flicker) — hold, don't switch yet

            self.locked_center = None  # truly lost — fall through to acquire a new target

        if all_target:
            self.locked_center = all_target["center"]
            self.last_seen_time = time.time()
        return all_target

    def _all_candidates(self, boxes, model_names, w, h):
        entries = []
        for box in boxes:
            cls_id = int(box.cls[0])
            cls_name = model_names.get(cls_id, "")
            if cls_name not in ("player", "head"):
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            entries.append({
                "class": cls_name, "center": center,
                "confidence": float(box.conf[0]), "bbox": (x1, y1, x2, y2),
                "distance_to_crosshair": math.hypot(center[0] - w/2, center[1] - h/2),
            })
        return entries

    def _find_closest(self, candidates, point):
        best = None
        best_dist = float("inf")
        for c in candidates:
            d = math.hypot(c["center"][0] - point[0], c["center"][1] - point[1])
            if d < best_dist:
                best_dist = d
                best = c
        if best is None:
            return None
        best["used_class"] = best["class"]
        return {"entry": best, "distance_to_lock": best_dist, "center": best["center"]}
