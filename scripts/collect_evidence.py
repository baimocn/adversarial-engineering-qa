#!/usr/bin/env python3
"""Build a deterministic, read-only evidence manifest and context shards.

The AST data is syntactic indexing only. It is not a resolved call graph and
must not be used as proof that dynamic dispatch or framework wiring is covered.
"""

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
DECLARATION_EXTENSIONS = {
    ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".cfg", ".ini",
    ".py", ".sh", ".ps1", ".dockerfile",
}
DECLARATION_RE = re.compile(
    r"command|entry.?point|dev_score|hidden_score|subprocess|timeout|"
    r"isolat|enforc|hidden|不可|不得|无法|命令|隔离|超时|评分|入口",
    re.IGNORECASE,
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


class PythonIndexer(ast.NodeVisitor):
    def __init__(self):
        self.scope = []
        self.definitions = []
        self.calls = []
        self.imports = []

    @property
    def current_scope(self):
        return ".".join(self.scope)

    def visit_ClassDef(self, node):
        qualname = ".".join(self.scope + [node.name])
        self.definitions.append({
            "kind": "class", "name": node.name, "qualname": qualname,
            "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno),
        })
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def _visit_function(self, node, kind):
        qualname = ".".join(self.scope + [node.name])
        args = [arg.arg for arg in node.args.posonlyargs + node.args.args]
        args.extend([arg.arg for arg in node.args.kwonlyargs])
        self.definitions.append({
            "kind": kind, "name": node.name, "qualname": qualname,
            "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno),
            "args": args,
        })
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self._visit_function(node, "function")

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node, "async_function")

    def visit_Call(self, node):
        name = dotted_name(node.func)
        if name:
            self.calls.append({
                "name": name, "scope": self.current_scope,
                "line": getattr(node, "lineno", 1),
            })
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({"module": alias.name, "alias": alias.asname, "line": node.lineno})
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.imports.append({
            "module": node.module, "alias": None, "level": node.level,
            "names": [alias.name for alias in node.names], "line": node.lineno,
        })
        self.generic_visit(node)


def read_text_sample(path, max_source_bytes):
    with path.open("rb") as handle:
        data = handle.read(max_source_bytes + 1)
    truncated = len(data) > max_source_bytes
    if truncated:
        data = data[:max_source_bytes]
    return data.decode("utf-8", errors="replace"), truncated


def index_python(path, relative_path, text):
    result = {"path": relative_path, "definitions": [], "calls": [], "imports": [], "syntax_error": None}
    try:
        tree = ast.parse(text, filename=relative_path)
    except (SyntaxError, ValueError) as exc:
        result["syntax_error"] = {"line": getattr(exc, "lineno", 1), "message": str(exc)}
        return result
    indexer = PythonIndexer()
    indexer.visit(tree)
    result["definitions"] = indexer.definitions
    result["calls"] = indexer.calls
    result["imports"] = indexer.imports
    return result


def should_exclude(relative_path, patterns):
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


def collect(root, max_files_per_shard=80, max_source_bytes=4 * 1024 * 1024, exclude_patterns=None):
    root = root.resolve()
    exclude_patterns = exclude_patterns or []
    files = []
    python_records = []
    declarations = []
    skipped = []

    if root.is_file():
        candidates = [root]
        base = root.parent
    else:
        candidates = []
        base = root
        for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            kept_dirs = []
            for dirname in sorted(dirnames):
                candidate = current_path / dirname
                rel = candidate.relative_to(base).as_posix()
                if dirname in DEFAULT_EXCLUDED_DIRS or should_exclude(rel, exclude_patterns):
                    skipped.append({"path": rel, "reason": "excluded_directory"})
                elif candidate.is_symlink():
                    skipped.append({"path": rel, "reason": "symlink_directory_not_followed"})
                else:
                    kept_dirs.append(dirname)
            dirnames[:] = kept_dirs
            for filename in sorted(filenames):
                candidates.append(current_path / filename)

    for path in sorted(candidates, key=lambda p: p.relative_to(base).as_posix()):
        rel = path.relative_to(base).as_posix()
        if should_exclude(rel, exclude_patterns):
            skipped.append({"path": rel, "reason": "excluded_file"})
            continue
        record = {"path": rel, "size_bytes": None, "sha256": None, "type": "regular"}
        if path.is_symlink():
            record.update({"type": "symlink", "target": os.readlink(path)})
            files.append(record)
            continue
        if not path.is_file():
            record["type"] = "special_or_unreadable"
            files.append(record)
            continue
        try:
            record["size_bytes"] = path.stat().st_size
            record["sha256"] = sha256_file(path)
        except OSError as exc:
            record["error"] = str(exc)
            files.append(record)
            continue

        suffix = path.suffix.lower()
        is_text_candidate = suffix in DECLARATION_EXTENSIONS or path.name.lower() == "dockerfile"
        if is_text_candidate:
            try:
                text, truncated = read_text_sample(path, max_source_bytes)
                record["text_sample_truncated"] = truncated
                if suffix == ".py":
                    if truncated:
                        py_record = {
                            "path": rel, "definitions": [], "calls": [], "imports": [],
                            "syntax_error": None, "sample_truncated": True,
                            "analysis_skipped": "source_exceeds_configured_limit",
                        }
                    else:
                        py_record = index_python(path, rel, text)
                        py_record["sample_truncated"] = False
                    python_records.append(py_record)
                for line_number, line in enumerate(text.splitlines(), 1):
                    if DECLARATION_RE.search(line):
                        declarations.append({
                            "path": rel, "line": line_number,
                            "text": line.strip()[:500],
                            "sample_truncated": truncated,
                        })
            except OSError as exc:
                record["text_error"] = str(exc)
        files.append(record)

    python_by_path = {record["path"]: record for record in python_records}
    declarations_by_path = defaultdict(list)
    for declaration in declarations:
        declarations_by_path[declaration["path"]].append(declaration)

    groups = defaultdict(list)
    for record in files:
        parts = Path(record["path"]).parts
        group = parts[0] if len(parts) > 1 else "root"
        groups[group].append(record)

    shards = []
    shard_number = 1
    for group in sorted(groups):
        group_files = sorted(groups[group], key=lambda item: item["path"])
        for start in range(0, len(group_files), max_files_per_shard):
            chunk = group_files[start:start + max_files_per_shard]
            shard_id = f"shard-{shard_number:04d}"
            shard_records = []
            for record in chunk:
                enriched = dict(record)
                py_record = python_by_path.get(record["path"])
                if py_record:
                    enriched["python"] = py_record
                if declarations_by_path.get(record["path"]):
                    enriched["declarations"] = declarations_by_path[record["path"]]
                shard_records.append(enriched)
            shards.append({
                "id": shard_id, "group": group,
                "path": f"shards/{shard_id}.json", "files": shard_records,
            })
            shard_number += 1

    symbols = []
    for py_record in python_records:
        for definition in py_record["definitions"]:
            symbols.append({
                "path": py_record["path"], "qualname": definition["qualname"],
                "kind": definition["kind"], "line": definition["line"],
            })
    symbols.sort(key=lambda item: (item["qualname"], item["path"], item["line"]))

    identity_records = [
        {"path": item["path"], "sha256": item.get("sha256"), "size_bytes": item.get("size_bytes"),
         "type": item.get("type"), "target": item.get("target"), "error": item.get("error")}
        for item in files
    ]
    identity_json = json.dumps(identity_records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_digest = hashlib.sha256(identity_json.encode("utf-8")).hexdigest()
    syntax_errors = [
        {"path": record["path"], **record["syntax_error"]}
        for record in python_records if record["syntax_error"]
    ]
    manifest = {
        "schema_version": "1.0",
        "root_name": root.name,
        "source_digest": source_digest,
        "digest_scope": "relative path, type, size and SHA-256 for all indexed entries",
        "files_total": len(files),
        "python_files_indexed": sum(1 for record in python_records if not record.get("analysis_skipped")),
        "python_files_skipped": sum(1 for record in python_records if record.get("analysis_skipped")),
        "declaration_candidates": len(declarations),
        "syntax_errors": syntax_errors,
        "skipped": skipped,
        "files": files,
        "shards": [{"id": s["id"], "group": s["group"], "path": s["path"], "file_count": len(s["files"])} for s in shards],
        "limitations": [
            "AST calls are syntactic candidates, not a resolved call graph",
            "Dynamic dispatch, reflection, framework registration and runtime configuration require separate review",
            "Large source files may have only a bounded text sample; inspect them separately",
        ],
    }
    return manifest, shards, symbols


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="File or directory to index without executing it")
    parser.add_argument("--out", required=True, help="Output directory outside the reviewed artifact")
    parser.add_argument("--max-files-per-shard", type=int, default=80)
    parser.add_argument("--max-source-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--exclude", action="append", default=[], help="Additional relative-path glob; repeatable")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.exists():
        parser.error(f"Root does not exist: {root}")
    if args.max_files_per_shard < 1 or args.max_source_bytes < 1:
        parser.error("Size limits must be positive")

    manifest, shards, symbols = collect(
        root, args.max_files_per_shard, args.max_source_bytes, args.exclude,
    )
    out = Path(args.out).resolve()
    if out == root.resolve() or (root.is_dir() and root.resolve() in out.parents):
        parser.error("Output directory must be outside the reviewed artifact")
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "manifest.json", manifest)
    for shard in shards:
        write_json(out / shard["path"], {
            "id": shard["id"], "group": shard["group"], "files": shard["files"],
        })
    write_json(out / "symbols.json", symbols)
    print(json.dumps({
        "manifest": str(out / "manifest.json"),
        "source_digest": manifest["source_digest"],
        "files_total": manifest["files_total"],
        "python_files_indexed": manifest["python_files_indexed"],
        "declaration_candidates": manifest["declaration_candidates"],
        "shards": len(shards),
        "syntax_errors": len(manifest["syntax_errors"]),
        "skipped": len(manifest["skipped"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
