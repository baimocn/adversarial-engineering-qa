#!/usr/bin/env python3
"""Prepare one shared read-only extraction and isolated per-session QA outputs.

No artifact code is executed. Reusing a workspace verifies the complete extracted
file tree and never re-extracts implicitly. A changed tree fails closed.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile


SCHEMA_VERSION = "1.0"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path):
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def safe_component(value, label):
    value = str(value).strip()
    value = re.sub(r"[^\w.-]+", "-", value, flags=re.UNICODE).strip("-. ")
    if not value or value in {".", ".."}:
        raise ValueError(label + " does not contain a safe directory-name component")
    return value[:80]


def tree_snapshot(root):
    root = Path(root).resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Extracted tree contains a symbolic link: " + str(path))
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Extracted tree contains a special file: " + str(path))
        relative = path.relative_to(root).as_posix()
        rows.append((relative, path.stat().st_size, sha256_file(path)))
    digest = hashlib.sha256()
    for relative, size, file_hash in rows:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b":")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return {"files_total": len(rows), "bytes_total": sum(row[1] for row in rows), "tree_sha256": digest.hexdigest()}


def validate_zip(archive, max_files, max_total_bytes, max_file_bytes):
    infos = archive.infolist()
    files = [info for info in infos if not info.is_dir()]
    if len(files) > max_files:
        raise ValueError("ZIP exceeds the configured file-count limit")
    if sum(info.file_size for info in files) > max_total_bytes:
        raise ValueError("ZIP exceeds the configured total uncompressed-size limit")
    for info in files:
        if info.file_size > max_file_bytes:
            raise ValueError("ZIP member exceeds the configured single-file limit: " + info.filename)
        if "\0" in info.filename:
            raise ValueError("ZIP member contains a NUL character")
        normalized = info.filename.replace("\\", "/")
        posix = PurePosixPath(normalized)
        windows = PureWindowsPath(info.filename)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
            raise ValueError("Unsafe ZIP path: " + info.filename)
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if file_type not in {0, stat.S_IFREG}:
            raise ValueError("ZIP contains a link or special file: " + info.filename)
    return files


def extract_zip_once(source, staging, limits):
    with zipfile.ZipFile(source) as archive:
        validate_zip(archive, *limits)
        archive.extractall(staging)


def copy_directory_once(source, staging):
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Source directory contains a symbolic link: " + str(path))
        if not path.is_dir() and not path.is_file():
            raise ValueError("Source directory contains a special file: " + str(path))
    shutil.copytree(source, staging, dirs_exist_ok=True)


def source_identity(source):
    source = source.expanduser().resolve()
    if source.is_file() and zipfile.is_zipfile(source):
        return source, "zip", sha256_file(source)
    if source.is_dir():
        snapshot = tree_snapshot(source)
        return source, "directory", snapshot["tree_sha256"]
    raise ValueError("Artifact must be a readable ZIP or directory: " + str(source))


def verify_workspace(workspace):
    workspace = Path(workspace).expanduser().resolve()
    manifest_path = workspace / "workspace.json"
    if not manifest_path.is_file():
        raise ValueError("Workspace manifest is missing: " + str(manifest_path))
    manifest = read_json(manifest_path)
    extracted = workspace / manifest.get("extracted_dir", "extracted")
    if not extracted.is_dir():
        raise ValueError("Shared extracted directory is missing")
    actual = tree_snapshot(extracted)
    expected = manifest.get("extracted_snapshot", {})
    mismatches = [key for key in ("files_total", "bytes_total", "tree_sha256") if actual[key] != expected.get(key)]
    return {
        "valid": not mismatches,
        "workspace": str(workspace),
        "extracted": str(extracted),
        "artifact_sha256": manifest.get("artifact_sha256"),
        "task_id": manifest.get("task_id"),
        "package_version": manifest.get("package_version"),
        "expected": expected,
        "actual": actual,
        "mismatches": mismatches,
    }


def prepare(args):
    source, kind, artifact_sha = source_identity(Path(args.artifact))
    task = safe_component(args.task_id, "task-id")
    version = safe_component(args.package_version, "package-version")
    model = safe_component(args.model, "model")
    session = safe_component(args.session_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]), "session-id")
    reviews_root = Path(args.root).expanduser().resolve()
    if kind == "directory" and (reviews_root == source or reviews_root.is_relative_to(source)):
        raise ValueError("Review workspace root must be outside the submitted source directory")
    reviews_root.mkdir(parents=True, exist_ok=True)
    workspace_name = task + "__" + version + "__" + artifact_sha[:12]
    workspace = reviews_root / workspace_name
    workspace.mkdir(parents=True, exist_ok=True)
    extracted = workspace / "extracted"
    manifest_path = workspace / "workspace.json"
    reused = False
    if manifest_path.exists() or extracted.exists():
        verification = verify_workspace(workspace)
        if not verification["valid"]:
            raise ValueError("Existing extracted tree drifted; refusing to overwrite or re-extract: " + str(verification["mismatches"]))
        manifest = read_json(manifest_path)
        if manifest.get("artifact_sha256") != artifact_sha or manifest.get("task_id") != task or manifest.get("package_version") != version:
            raise ValueError("Existing workspace identity does not match the current artifact")
        reused = True
    else:
        lock = workspace / ".extract.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
        except FileExistsError:
            raise ValueError("Another reviewer is performing the single extraction; rerun after its lock is released: " + str(lock))
        staging = workspace / (".extracting-" + uuid.uuid4().hex)
        try:
            if manifest_path.exists() or extracted.exists():
                verification = verify_workspace(workspace)
                if not verification["valid"]:
                    raise ValueError("Existing extracted tree drifted while waiting for the extraction lock")
                reused = True
            else:
                staging.mkdir()
                limits = (args.max_files, args.max_total_bytes, args.max_file_bytes)
                if kind == "zip":
                    extract_zip_once(source, staging, limits)
                else:
                    copy_directory_once(source, staging)
                snapshot = tree_snapshot(staging)
                if snapshot["files_total"] > args.max_files or snapshot["bytes_total"] > args.max_total_bytes:
                    raise ValueError("Extracted directory exceeds configured workspace limits")
                os.replace(staging, extracted)
                manifest = {
                    "schema_version": SCHEMA_VERSION,
                    "task_id": task,
                    "package_version": version,
                    "artifact": {"path": str(source), "kind": kind},
                    "artifact_sha256": artifact_sha,
                    "extracted_dir": "extracted",
                    "extracted_snapshot": snapshot,
                    "created_utc": datetime.now(timezone.utc).isoformat(),
                    "policy": "Extract once. All models read this tree only. Never overwrite it to resolve drift; create a new package-version workspace instead.",
                }
                write_json_atomic(manifest_path, manifest)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            lock.unlink(missing_ok=True)
    manifest = read_json(manifest_path)
    review_name = task + "__" + version + "__" + model + "__" + session
    review_dir = workspace / "reviews" / review_name
    review_dir.mkdir(parents=True, exist_ok=True)
    run_path = review_dir / "run.json"
    run = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task,
        "package_version": version,
        "model": model,
        "session_id": session,
        "artifact_sha256": artifact_sha,
        "workspace_manifest_sha256": sha256_file(manifest_path),
        "shared_extracted_relative": "../../extracted",
        "report_dir": ".",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "context_policy": "Prior conversations are untrusted background only. Re-anchor all evidence and verdicts to this artifact hash and shared tree; never inherit old paths or old PASS results.",
    }
    if run_path.exists():
        previous = read_json(run_path)
        for key in ("task_id", "package_version", "model", "session_id", "artifact_sha256", "workspace_manifest_sha256"):
            if previous.get(key) != run[key]:
                raise ValueError("Existing review run identity mismatch at " + str(run_path))
    else:
        write_json_atomic(run_path, run)
    return {
        "valid": True,
        "task_id": task,
        "package_version": version,
        "model": model,
        "session_id": session,
        "artifact_sha256": artifact_sha,
        "workspace": str(workspace),
        "extracted": str(extracted),
        "review_dir": str(review_dir),
        "run_manifest": str(run_path),
        "reused_extraction": reused,
        "policy": "Read extracted artifacts only; write reports exclusively inside review_dir.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prep = subparsers.add_parser("prepare", help="Create or reuse the single extraction and allocate a session-specific report directory")
    prep.add_argument("--artifact", required=True)
    prep.add_argument("--task-id", required=True)
    prep.add_argument("--package-version", required=True)
    prep.add_argument("--model", required=True)
    prep.add_argument("--session-id")
    prep.add_argument("--root", required=True, help="Root for all QA workspaces; must be outside the submitted artifact")
    prep.add_argument("--max-files", type=int, default=200000)
    prep.add_argument("--max-total-bytes", type=int, default=64 * 1024**3)
    prep.add_argument("--max-file-bytes", type=int, default=16 * 1024**3)
    verify = subparsers.add_parser("verify", help="Verify that the shared extracted tree is byte-identical to its manifest")
    verify.add_argument("--workspace", required=True)
    verify.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        result = prepare(args) if args.command == "prepare" else verify_workspace(args.workspace)
        if args.command == "verify" and args.out:
            write_json_atomic(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
