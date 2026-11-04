#!/usr/bin/env python3
"""Statically check fixed Python return arity against tuple/list unpacking.

This is a contract-candidate scanner, not a type checker. Dynamic returns,
starred expressions and unresolved calls remain explicit coverage limitations.
No reviewed module is imported or executed.
"""

import argparse
import ast
import json
import os
import sys
from pathlib import Path

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def fixed_return_arity(node):
    if node.value is None:
        return 1
    value = node.value
    if isinstance(value, (ast.Tuple, ast.List)):
        if any(isinstance(element, ast.Starred) for element in value.elts):
            return None
        return len(value.elts)
    return 1


class ReturnCollector(ast.NodeVisitor):
    def __init__(self):
        self.returns = []

    def visit_Return(self, node):
        self.returns.append({
            "line": node.lineno,
            "arity": fixed_return_arity(node),
        })

    def visit_FunctionDef(self, node):
        return

    def visit_AsyncFunctionDef(self, node):
        return

    def visit_Lambda(self, node):
        return

    def visit_ClassDef(self, node):
        return


class ModuleCollector(ast.NodeVisitor):
    def __init__(self, module, path):
        self.module = module
        self.path = path
        self.scope = []
        self.class_scope = []
        self.functions = []
        self.unpack_calls = []
        self.import_aliases = {}
        self.from_imports = {}

    def visit_Import(self, node):
        for alias in node.names:
            self.import_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.from_imports[alias.asname or alias.name] = {
                    "module": node.module, "name": alias.name, "level": node.level,
                }
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.class_scope.append(node.name)
        self.generic_visit(node)
        self.class_scope.pop()
        self.scope.pop()

    def _visit_function(self, node, kind):
        qualname = ".".join(self.scope + [node.name])
        collector = ReturnCollector()
        for statement in node.body:
            collector.visit(statement)
        self.functions.append({
            "module": self.module, "path": self.path, "name": node.name,
            "qualname": qualname, "kind": kind, "line": node.lineno,
            "returns": collector.returns,
        })
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self._visit_function(node, "function")

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node, "async_function")

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], (ast.Tuple, ast.List)):
            target = node.targets[0]
            if not any(isinstance(element, ast.Starred) for element in target.elts):
                value = node.value.value if isinstance(node.value, ast.Await) else node.value
                if isinstance(value, ast.Call):
                    name = dotted_name(value.func)
                    if name:
                        self.unpack_calls.append({
                            "module": self.module, "path": self.path,
                            "line": node.lineno, "call": name,
                            "expected_arity": len(target.elts),
                            "scope": ".".join(self.scope),
                            "class_scope": self.class_scope[-1] if self.class_scope else None,
                        })
        self.generic_visit(node)


def module_name_for(path, base):
    rel = path.relative_to(base).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def python_files(root, max_source_bytes):
    skipped = []
    if root.is_file():
        candidates = [root]
        base = root.parent
    else:
        candidates = []
        base = root
        for current, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_DIRS)
            for filename in sorted(filenames):
                if filename.endswith(".py"):
                    candidates.append(Path(current) / filename)
    selected = []
    for path in sorted(candidates):
        if path.stat().st_size > max_source_bytes:
            skipped.append({"path": str(path), "reason": "source_exceeds_configured_limit"})
        else:
            selected.append(path)
    return selected, base, skipped


def resolve_call(call, functions_by_key, functions_by_module_name, imports):
    module = call["module"]
    name = call["call"]
    short_name = name.rsplit(".", 1)[-1]
    same_module = functions_by_module_name.get((module, short_name), [])

    if "." not in name:
        if len(same_module) == 1:
            return same_module[0], "same_module"
        imported = imports["from"].get(name)
        if imported and imported["level"] == 0:
            candidates = functions_by_module_name.get((imported["module"], imported["name"]), [])
            if len(candidates) == 1:
                return candidates[0], "from_import"
        candidates = [info for (mod, func), values in functions_by_module_name.items() if func == short_name for info in values]
        if len(candidates) == 1:
            return candidates[0], "unique_global_name"
        return None, "unresolved_or_ambiguous_name"

    if name.startswith("self.") and call["class_scope"]:
        wanted = f"{call['class_scope']}.{short_name}"
        candidates = [info for info in same_module if info["qualname"].endswith(wanted)]
        if len(candidates) == 1:
            return candidates[0], "same_class_method"
        return None, "unresolved_method"

    root_name = name.split(".", 1)[0]
    if root_name in imports["direct"]:
        imported_module = imports["direct"][root_name]
        candidates = functions_by_module_name.get((imported_module, short_name), [])
        if len(candidates) == 1:
            return candidates[0], "imported_module_attribute"
    candidates = [info for info in same_module if info["qualname"].endswith(name)]
    if len(candidates) == 1:
        return candidates[0], "same_module_attribute"
    return None, "unresolved_or_ambiguous_attribute"


def analyze(root, max_source_bytes=4 * 1024 * 1024):
    root = Path(root).resolve()
    paths, base, skipped = python_files(root, max_source_bytes)
    functions = []
    calls = []
    imports_by_module = {}
    syntax_errors = []
    parse_failures = []

    for path in paths:
        rel = path.relative_to(base).as_posix()
        module = module_name_for(path, base)
        try:
            text = path.read_text(encoding="utf-8-sig")
            tree = ast.parse(text, filename=rel)
        except (OSError, UnicodeError) as exc:
            parse_failures.append({"path": rel, "message": str(exc)})
            continue
        except SyntaxError as exc:
            syntax_errors.append({"path": rel, "line": exc.lineno, "message": str(exc)})
            continue
        collector = ModuleCollector(module, rel)
        collector.visit(tree)
        functions.extend(collector.functions)
        calls.extend(collector.unpack_calls)
        imports_by_module[module] = {
            "direct": collector.import_aliases, "from": collector.from_imports,
        }

    functions_by_key = {(info["module"], info["qualname"]): info for info in functions}
    functions_by_module_name = {}
    for info in functions:
        functions_by_module_name.setdefault((info["module"], info["name"]), []).append(info)

    findings = []
    checked_calls = []
    unresolved_calls = []
    for call in calls:
        function, resolution = resolve_call(
            call, functions_by_key, functions_by_module_name,
            imports_by_module.get(call["module"], {"direct": {}, "from": {}}),
        )
        if not function:
            unresolved_calls.append({**call, "reason": resolution})
            continue
        fixed_arities = sorted({item["arity"] for item in function["returns"] if item["arity"] is not None})
        unknown_returns = [item for item in function["returns"] if item["arity"] is None]
        if not fixed_arities:
            unresolved_calls.append({**call, "reason": "no_statically_fixed_return_arity", "function": function["qualname"]})
            continue
        checked_calls.append({
            **call, "function": function["qualname"], "function_path": function["path"],
            "possible_arities": fixed_arities, "resolution": resolution,
        })
        if fixed_arities != [call["expected_arity"]]:
            findings.append({
                "kind": "return_arity_mismatch",
                "confidence": "confirmed_static" if not unknown_returns else "candidate_with_dynamic_returns",
                "function": function["qualname"], "function_path": function["path"],
                "function_line": function["line"], "caller_path": call["path"],
                "caller_line": call["line"], "call": call["call"],
                "expected_arity": call["expected_arity"], "possible_arities": fixed_arities,
                "return_points": function["returns"], "resolution": resolution,
            })

    return {
        "schema_version": "1.0",
        "root": str(root),
        "files_indexed": len(paths),
        "functions_indexed": len(functions),
        "unpack_calls_indexed": len(calls),
        "checked_calls": checked_calls,
        "unresolved_calls": unresolved_calls,
        "findings": findings,
        "syntax_errors": syntax_errors,
        "parse_failures": parse_failures,
        "skipped": skipped,
        "limitations": [
            "Only fixed tuple/list returns and direct tuple/list unpacking are checked",
            "Dynamic returns, starred values and unresolved calls are not proven correct",
            "Unique-name and import resolution are static heuristics; inspect each finding",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Python file or source directory")
    parser.add_argument("--out", required=True, help="JSON output outside the reviewed artifact")
    parser.add_argument("--max-source-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.exists():
        parser.error(f"Root does not exist: {root}")
    result = analyze(root, args.max_source_bytes)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(out), "files_indexed": result["files_indexed"],
        "functions_indexed": result["functions_indexed"],
        "unpack_calls_indexed": result["unpack_calls_indexed"],
        "checked_calls": len(result["checked_calls"]),
        "unresolved_calls": len(result["unresolved_calls"]),
        "findings": len(result["findings"]),
        "syntax_errors": len(result["syntax_errors"]),
    }, ensure_ascii=False, indent=2))
    return 1 if args.fail_on_findings and result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
