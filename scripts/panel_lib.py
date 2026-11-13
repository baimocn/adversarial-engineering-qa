#!/usr/bin/env python3
"""Deterministic support for the 2+1 subjective-review protocol.

The model panel produces judgment JSON; this module only validates evidence and
applies the fixed agreement/adjudication rules. It never calls a model.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

VALID_VERDICTS = {"pass", "fail", "unknown"}
MAX_EVIDENCE_BYTES = 8_000_000


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_path(root: Path, rel: str) -> Path | None:
    if not isinstance(rel, str) or not rel.strip():
        return None
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        return None
    return candidate


def _resolve_pointer(data, pointer: str):
    if pointer in ("", "/"):
        return data, True
    if not pointer.startswith("/"):
        return None, False
    cur = data
    for raw in pointer[1:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            try:
                cur = cur[int(key)]
            except (ValueError, IndexError):
                return None, False
        elif isinstance(cur, dict):
            if key not in cur:
                return None, False
            cur = cur[key]
        else:
            return None, False
    return cur, True


def validate_evidence(root: Path, evidence: list) -> list[str]:
    """Return a list of errors; empty means every evidence item is verifiable."""
    errors: list[str] = []
    if not isinstance(evidence, list):
        return ["evidence must be a list"]
    for index, item in enumerate(evidence):
        label = f"evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: not an object")
            continue
        path = _safe_path(root, item.get("path"))
        if path is None:
            errors.append(f"{label}: path missing, absolute, or escapes the task root")
            continue
        if not path.is_file():
            errors.append(f"{label}: file not found: {item.get('path')}")
            continue
        if path.stat().st_size > MAX_EVIDENCE_BYTES:
            errors.append(f"{label}: file too large for evidence (> {MAX_EVIDENCE_BYTES} bytes)")
            continue

        if "line" in item:
            line = item.get("line")
            quote = item.get("quote")
            if not isinstance(line, int) or isinstance(line, bool) or line < 1:
                errors.append(f"{label}: line must be a positive integer")
                continue
            if not isinstance(quote, str) or not normalize_ws(quote):
                errors.append(f"{label}: line evidence needs a non-empty quote")
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line > len(lines):
                errors.append(f"{label}: line {line} beyond file length {len(lines)}")
                continue
            if normalize_ws(quote) not in normalize_ws(lines[line - 1]):
                errors.append(f"{label}: quote not found on {item.get('path')}:{line}")
        elif "pointer" in item:
            pointer = item.get("pointer")
            if not isinstance(pointer, str):
                errors.append(f"{label}: pointer must be a string")
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"{label}: not JSON ({exc})")
                continue
            _, ok = _resolve_pointer(data, pointer)
            if not ok:
                errors.append(f"{label}: pointer does not resolve: {pointer}")
        elif "value" in item:
            needle = item.get("value")
            if not isinstance(needle, str) or not needle:
                errors.append(f"{label}: value must be a non-empty string")
                continue
            if needle not in path.read_text(encoding="utf-8", errors="replace"):
                errors.append(f"{label}: value not found in {item.get('path')}")
        else:
            errors.append(f"{label}: needs line+quote, pointer, or value")
    return errors


def validate_judgment(root: Path, obj, expected_item: str | None = None) -> dict:
    errors: list[str] = []
    if not isinstance(obj, dict):
        return {"ok": False, "errors": ["judgment is not an object"], "evidence_ok": False}
    item_id = obj.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        errors.append("item_id missing")
    if expected_item is not None and item_id != expected_item:
        errors.append(f"item_id mismatch: expected {expected_item}, got {item_id}")
    if not isinstance(obj.get("model"), str) or not obj.get("model"):
        errors.append("model missing")
    verdict = obj.get("verdict")
    if verdict not in VALID_VERDICTS:
        errors.append(f"verdict must be one of {sorted(VALID_VERDICTS)}")
    evidence_errors = validate_evidence(root, obj.get("evidence") or [])
    if not obj.get("evidence"):
        errors.append("evidence missing")
    return {
        "ok": not errors and not evidence_errors,
        "errors": errors + evidence_errors,
        "evidence_ok": not evidence_errors and bool(obj.get("evidence")),
        "verdict": verdict,
        "model": obj.get("model"),
    }


def validate_adjudication(root: Path, obj, item_id: str, a: dict, b: dict) -> dict:
    errors: list[str] = []
    if not isinstance(obj, dict):
        return {"ok": False, "errors": ["adjudication is not an object"]}
    if obj.get("item_id") != item_id:
        errors.append("item_id mismatch")
    if not isinstance(obj.get("model"), str) or not obj.get("model"):
        errors.append("model missing")
    winner = obj.get("winner")
    if winner not in ("A", "B"):
        errors.append("winner must be A or B")
    verdict = obj.get("verdict")
    if verdict not in VALID_VERDICTS:
        errors.append("verdict must be pass, fail, or unknown")
    else:
        expected = a.get("verdict") if winner == "A" else b.get("verdict")
        if verdict != expected:
            errors.append(f"verdict {verdict!r} does not match winner {winner} ({expected!r})")
    evidence_errors = validate_evidence(root, obj.get("evidence") or [])
    if not obj.get("evidence"):
        errors.append("adjudication evidence missing")
    if not isinstance(obj.get("reason"), str) or not obj.get("reason").strip():
        errors.append("reason missing")
    return {"ok": not errors and not evidence_errors, "errors": errors + evidence_errors}


def decide_panel(root: Path, a: dict, b: dict, adjudication: dict | None = None) -> dict:
    item_id = (a or {}).get("item_id") or (b or {}).get("item_id") or ""
    va = validate_judgment(root, a, item_id)
    vb = validate_judgment(root, b, item_id)
    result = {
        "schema": "panel-decision/1",
        "item_id": item_id,
        "judges": {
            "A": {"model": va.get("model"), "verdict": va.get("verdict"),
                  "valid": va["ok"], "errors": va["errors"]},
            "B": {"model": vb.get("model"), "verdict": vb.get("verdict"),
                  "valid": vb["ok"], "errors": vb["errors"]},
        },
        "adjudication": None,
        "category": "human_required",
        "verdict": "unknown",
        "errors": [],
    }

    if va["ok"] and vb["ok"] and va["verdict"] == vb["verdict"] and va["verdict"] != "unknown":
        result["category"] = "judged_agree"
        result["verdict"] = va["verdict"]
        return result

    if adjudication is not None:
        adj = validate_adjudication(root, adjudication, item_id, a, b)
        result["adjudication"] = {
            "model": adjudication.get("model") if isinstance(adjudication, dict) else None,
            "winner": adjudication.get("winner") if isinstance(adjudication, dict) else None,
            "verdict": adjudication.get("verdict") if isinstance(adjudication, dict) else None,
            "valid": adj["ok"],
            "errors": adj["errors"],
        }
        if adj["ok"] and adjudication.get("verdict") != "unknown":
            result["category"] = "judged_adjudicated"
            result["verdict"] = adjudication["verdict"]
            return result

    result["errors"] = va["errors"] + vb["errors"]
    return result
