from pathlib import Path
from collections import Counter
import yaml

def count_classes(root: Path):
    print(f"\n{'='*60}\n{root}\n{'='*60}")
    yaml_path = root / "data.yaml"
    with open(yaml_path) as f:
        names = yaml.safe_load(f).get("names")

    total_files = 0
    empty_files = 0
    class_counts = Counter()

    for split in ["train", "valid", "test"]:
        lbl_dir = root / split / "labels"
        if not lbl_dir.exists():
            continue
        for lbl_file in lbl_dir.glob("*.txt"):
            total_files += 1
            content = lbl_file.read_text().strip()
            if not content:
                empty_files += 1
                continue
            for line in content.splitlines():
                cls_id = int(line.split()[0])
                class_counts[cls_id] += 1

    print(f"Total label files: {total_files}  |  Empty (no objects): {empty_files} "
          f"({100*empty_files/total_files:.1f}%)")
    print("Instances per class:")
    for cls_id in sorted(class_counts):
        cls_name = names[cls_id] if cls_id < len(names) else f"id_{cls_id}"
        print(f"  [{cls_id}] {cls_name}: {class_counts[cls_id]} instances")


if __name__ == "__main__":
    base = Path("../data")
    for ds in [
        base / "stage1_raw" / "valorant_davidhong",
        base / "stage1_raw" / "csgo_aimbot_v5",
        base / "stage2_raw" / "csgo_team_split",
    ]:
        count_classes(ds)
