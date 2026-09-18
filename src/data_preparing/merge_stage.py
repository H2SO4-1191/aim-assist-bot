import shutil
from pathlib import Path
import yaml

SOURCES = [
    {
        "root": Path("../data/stage1_raw/valorant_davidhong"),
        "keep_class_id": 1,   # "enemy"
        "prefix": "val_",     # avoid filename collisions between datasets
    },
    {
        "root": Path("../data/stage1_raw/csgo_aimbot_v5"),
        "keep_class_id": 0,   # "terrorist"
        "prefix": "csgo_",
    },
]

OUT_ROOT = Path("../data/stage1_final")
SPLITS = ["train", "valid", "test"]


def remap_and_copy(label_path: Path, keep_class_id: int, out_label_path: Path):
    """Copy only boxes matching keep_class_id, remapped to class 0 (player)."""
    content = label_path.read_text().strip()
    if not content:
        out_label_path.write_text("")  # keep empty frames as negative examples
        return True

    kept_lines = []
    for line in content.splitlines():
        parts = line.split()
        cls_id = int(parts[0])
        if cls_id == keep_class_id:
            # remap to 0 (player), keep the rest of the box coords unchanged
            kept_lines.append("0 " + " ".join(parts[1:]))

    out_label_path.write_text("\n".join(kept_lines))
    return True


def main():
    for split in SPLITS:
        (OUT_ROOT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT_ROOT / "labels" / split).mkdir(parents=True, exist_ok=True)

    total_copied = 0
    total_boxes = 0

    for source in SOURCES:
        root = source["root"]
        keep_id = source["keep_class_id"]
        prefix = source["prefix"]

        for split in SPLITS:
            img_dir = root / split / "images"
            lbl_dir = root / split / "labels"
            if not img_dir.exists():
                continue

            for img_path in img_dir.glob("*.*"):
                lbl_path = lbl_dir / (img_path.stem + ".txt")
                if not lbl_path.exists():
                    continue

                new_name = prefix + img_path.name
                out_img = OUT_ROOT / "images" / split / new_name
                out_lbl = OUT_ROOT / "labels" / split / (prefix + img_path.stem + ".txt")

                shutil.copy(img_path, out_img)
                remap_and_copy(lbl_path, keep_id, out_lbl)

                total_copied += 1
                total_boxes += len(out_lbl.read_text().strip().splitlines()) if out_lbl.read_text().strip() else 0

    # write unified data.yaml
    data_yaml = {
        "path": str(OUT_ROOT.resolve()),
        "train": "images/train",
        "val": "images/valid",
        "test": "images/test",
        "names": {0: "player"},
    }
    with open(OUT_ROOT / "data.yaml", "w") as f:
        yaml.dump(data_yaml, f)

    print(f"Merged {total_copied} images, {total_boxes} player boxes total.")
    print(f"Output: {OUT_ROOT.resolve()}")
    print(f"data.yaml written with single class: player")


if __name__ == "__main__":
    main()
