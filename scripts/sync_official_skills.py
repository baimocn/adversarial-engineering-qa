#!/usr/bin/env python3
"""Check or explicitly refresh the bundled, unmodified official skill mirrors.

The source skills are only read. No submitted artifact code is executed. A hot
update is never applied implicitly during a review; --apply is required.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


SKILL_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_ROOT = SKILL_ROOT / "official"
SKILL_NAMES = [
    "autoresearch-task-qa-legacy-waiver",
    "autoresearch-baseline-quality",
    "autoresearch-supplement-platform-audit",
]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root):
    root = Path(root)
    rows = {}
    if not root.is_dir():
        return rows
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        rows[relative] = {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
    return rows


def validate_sources(source_root):
    errors = []
    for name in SKILL_NAMES:
        skill = source_root / name / "SKILL.md"
        if not skill.is_file():
            # 内嵌副本来自不同上游（supplement 不在官方发行包内）；
            # 源根缺某项不算错误，compare 会把它标为 not_in_source 跳过。
            continue
        text = skill.read_text(encoding="utf-8-sig")
        if ("name: " + name) not in text:
            errors.append("Source SKILL.md name mismatch: " + name)
    return errors


def compare(source_root):
    differences = {}
    for name in SKILL_NAMES:
        source_dir = source_root / name
        bundled = snapshot(BUNDLED_ROOT / name)
        if not (source_dir / "SKILL.md").is_file():
            differences[name] = {
                "source_files": 0,
                "bundled_files": len(bundled),
                "added": [], "removed": [], "changed": [],
                "identical": True,
                "not_in_source": True,
            }
            continue
        source = snapshot(source_dir)
        added = sorted(set(source) - set(bundled))
        removed = sorted(set(bundled) - set(source))
        changed = sorted(key for key in set(source) & set(bundled) if source[key] != bundled[key])
        differences[name] = {
            "source_files": len(source),
            "bundled_files": len(bundled),
            "added": added,
            "removed": removed,
            "changed": changed,
            "identical": not added and not removed and not changed,
        }
    return differences


def relocate_dir(source, destination):
    """Move a directory, tolerating cross-device layouts on Windows."""
    source = Path(source)
    destination = Path(destination)
    try:
        os.replace(source, destination)
    except OSError:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        shutil.rmtree(source)


def apply_update(source_root):
    """逐 skill 原子替换：源里没有的项（not_in_source）保持内嵌副本原样，不删除。"""
    present = [name for name in SKILL_NAMES
               if (source_root / name / "SKILL.md").is_file()]
    with tempfile.TemporaryDirectory(prefix=".official-sync-", dir=SKILL_ROOT) as temp:
        temp = Path(temp)
        BUNDLED_ROOT.mkdir(parents=True, exist_ok=True)
        replaced = []
        for name in present:
            staging = temp / name
            shutil.copytree(
                source_root / name,
                staging,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            if snapshot(source_root / name) != snapshot(staging):
                raise ValueError("Staged copy does not byte-match source: " + name)
            backup = temp / (name + "-backup")
            target = BUNDLED_ROOT / name
            if target.exists():
                relocate_dir(target, backup)
            try:
                relocate_dir(staging, target)
            except Exception:
                if backup.exists():
                    if target.exists():
                        shutil.rmtree(target)
                    relocate_dir(backup, target)
                raise
            replaced.append(name)
        if not replaced:
            raise ValueError("No source skill found in " + str(source_root))
        return replaced


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, help="Directory containing the official skill directories (task-qa / baseline-quality / supplement-platform-audit)")
    parser.add_argument("--apply", action="store_true", help="Explicitly replace the bundled mirrors after byte verification")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    source_root = Path(args.source_root).expanduser().resolve()
    errors = validate_sources(source_root)
    differences = compare(source_root) if not errors else {}
    update_available = bool(differences) and any(not row["identical"] for row in differences.values())
    applied = False
    if not errors and args.apply and update_available:
        apply_update(source_root)
        applied = True
        differences = compare(source_root)
    result = {
        "valid": not errors,
        "source_root": str(source_root),
        "bundled_root": str(BUNDLED_ROOT),
        "update_available": update_available,
        "applied": applied,
        "differences": differences,
        "errors": errors,
        "note": "Source skills are read-only. Review any version/rule change and update the compatibility contract explicitly; never auto-update during a review.",
    }
    if args.out:
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
