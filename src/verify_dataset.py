
from pathlib import Path
import yaml

def check_dataset(root: Path):
    print(f"\n{'='*60}\nChecking: {root}\n{'='*60}")

    yaml_path = root / "data.yaml"
    if not yaml_path.exists():
        print(f"[!] No data.yaml found at {yaml_path} — check you extracted the right folder")
        return

    with open(yaml_path) as f:
        data_cfg = yaml.safe_load(f)

    print(f"Classes: {data_cfg.get('names')}")

    for split in ["train", "valid", "test"]:
        split_dir = root / split
        if not split_dir.exists():
            print(f"  {split}: (not present)")
            continue

        img_dir = split_dir / "images"
        lbl_dir = split_dir / "labels"
        n_images = len(list(img_dir.glob("*.*"))) if img_dir.exists() else 0
        n_labels = len(list(lbl_dir.glob("*.txt"))) if lbl_dir.exists() else 0

        status = "OK" if n_images == n_labels else "MISMATCH — investigate"
        print(f"  {split}: {n_images} images, {n_labels} labels [{status}]")

        # spot-check one label file
        if lbl_dir.exists():
            label_files = list(lbl_dir.glob("*.txt"))
            if label_files:
                sample = label_files[0]
                content = sample.read_text().strip()
                print(f"    sample ({sample.name}): {content[:150] or '(empty - no objects in this frame)'}")


if __name__ == "__main__":
    base = Path("../data")
    datasets = [
        base / "stage1_raw" / "valorant_davidhong",
        base / "stage1_raw" / "csgo_aimbot_v5",
        base / "stage2_raw" / "csgo_team_split",
    ]
    for ds in datasets:
        check_dataset(ds)
