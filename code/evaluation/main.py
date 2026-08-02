"""Validate generated submission output and write an evaluation report."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

# Ensure repo root is importable when invoked as ``python evaluation/main.py`` from code/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.output.generator import OUTPUT_COLUMNS, VALID_ACTIONS, VALID_MESSAGE_TYPES

_DEFAULT_INPUT = _REPO_ROOT / "dataset" / "messages.csv"
_DEFAULT_OUTPUT = _REPO_ROOT / "dataset" / "output.csv"
_DEFAULT_REPORT = _REPO_ROOT / "evaluation_report.json"


def _resolve_path(path: Union[str, Path], default: Path) -> Path:
    """Resolve relative paths against cwd, then the repository root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate
    rooted = _REPO_ROOT / candidate
    if rooted.exists():
        return rooted
    return default if path in {"dataset/messages.csv", "dataset/output.csv", "evaluation_report.json"} else candidate


def evaluate_output(
    input_path: Union[str, Path, None] = None,
    output_path: Union[str, Path, None] = None,
    report_path: Union[str, Path, None] = None,
) -> Dict[str, Any]:
    """Validate a generated output CSV and save the resulting JSON report."""
    started_at = time.perf_counter()
    input_path = _resolve_path(input_path or _DEFAULT_INPUT, _DEFAULT_INPUT)
    output_path = _resolve_path(output_path or _DEFAULT_OUTPUT, _DEFAULT_OUTPUT)
    report_path = Path(report_path) if report_path is not None else _DEFAULT_REPORT
    if not report_path.is_absolute():
        report_path = (_REPO_ROOT / report_path) if not report_path.exists() else report_path

    expected_ids = _read_message_ids(input_path)
    actual_columns, output_rows = _read_output_rows(output_path)
    output_ids = [row.get("message_id", "") for row in output_rows]

    missing_values = _missing_values(output_rows)
    duplicate_ids = _duplicates(output_ids)
    failed_message_ids = _failed_message_ids(
        expected_ids, output_rows, missing_values, duplicate_ids
    )
    confidence_violations = _confidence_violations(output_rows)
    evidence_violations = _evidence_violations(output_rows)
    schema_errors = _schema_errors(actual_columns, output_rows)

    schema_valid = not schema_errors
    report = {
        "total_messages_processed": len(output_rows),
        "expected_messages": len(expected_ids),
        "failed_messages": sorted(failed_message_ids),
        "action_distribution": dict(sorted(Counter(row.get("action", "") for row in output_rows).items())),
        "confidence_distribution": _confidence_distribution(output_rows),
        "missing_values": missing_values,
        "duplicate_message_ids": duplicate_ids,
        "schema_validation": {
            "valid": schema_valid,
            "expected_columns": list(OUTPUT_COLUMNS),
            "actual_columns": actual_columns,
            "errors": schema_errors,
        },
        "confidence_violations": confidence_violations,
        "evidence_id_violations": evidence_violations,
        "execution_time_seconds": round(time.perf_counter() - started_at, 6),
        "is_valid": not (
            failed_message_ids
            or missing_values
            or duplicate_ids
            or schema_errors
            or confidence_violations
            or evidence_violations
        ),
    }

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _read_message_ids(path: Path) -> List[str]:
    with path.open(newline="", encoding="utf-8") as input_file:
        return [row["message_id"] for row in csv.DictReader(input_file)]


def _read_output_rows(path: Path) -> tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as output_file:
        reader = csv.DictReader(output_file)
        return reader.fieldnames or [], list(reader)


def _missing_values(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    missing = []
    for row in rows:
        missing_fields = [
            column for column in OUTPUT_COLUMNS
            if row.get(column) is None or not row[column].strip()
        ]
        if missing_fields:
            missing.append({"message_id": row.get("message_id", ""), "fields": missing_fields})
    return missing


def _duplicates(message_ids: Iterable[str]) -> List[str]:
    counts = Counter(message_ids)
    return sorted(message_id for message_id, count in counts.items() if count > 1 and message_id)


def _failed_message_ids(
    expected_ids: Iterable[str],
    rows: Iterable[Dict[str, str]],
    missing_values: Iterable[Dict[str, str]],
    duplicate_ids: Iterable[str],
) -> set[str]:
    output_ids = [row.get("message_id", "") for row in rows]
    failures = set(expected_ids) - set(output_ids)
    failures.update(set(output_ids) - set(expected_ids))
    failures.update(item["message_id"] for item in missing_values if item["message_id"])
    failures.update(duplicate_ids)
    return failures


def _confidence_violations(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    violations = []
    for row in rows:
        try:
            confidence = float(row.get("confidence", ""))
        except (TypeError, ValueError):
            violations.append({"message_id": row.get("message_id", ""), "value": row.get("confidence", "")})
            continue
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            violations.append({"message_id": row.get("message_id", ""), "value": row.get("confidence", "")})
    return violations


def _confidence_distribution(rows: Iterable[Dict[str, str]]) -> Dict[str, int]:
    """Count confidence values in fixed, inclusive lower-bound buckets."""
    buckets = {
        "0.00-0.24": 0,
        "0.25-0.49": 0,
        "0.50-0.74": 0,
        "0.75-1.00": 0,
        "invalid": 0,
    }
    for row in rows:
        try:
            confidence = float(row.get("confidence", ""))
        except (TypeError, ValueError):
            buckets["invalid"] += 1
            continue
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            buckets["invalid"] += 1
        elif confidence < 0.25:
            buckets["0.00-0.24"] += 1
        elif confidence < 0.50:
            buckets["0.25-0.49"] += 1
        elif confidence < 0.75:
            buckets["0.50-0.74"] += 1
        else:
            buckets["0.75-1.00"] += 1
    return buckets


def _evidence_violations(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    violations = []
    for row in rows:
        evidence = row.get("evidence_message_ids", "")
        if evidence == "none":
            continue
        if not evidence or any(not message_id.strip() for message_id in evidence.split(";")):
            violations.append({"message_id": row.get("message_id", ""), "value": evidence})
    return violations


def _schema_errors(columns: List[str], rows: Iterable[Dict[str, str]]) -> List[str]:
    errors = []
    if columns != list(OUTPUT_COLUMNS):
        errors.append("Output columns do not match the required schema and order.")
    for row in rows:
        message_id = row.get("message_id", "")
        if row.get("action") not in VALID_ACTIONS:
            errors.append(f"Invalid action for {message_id}.")
        if row.get("message_type") not in VALID_MESSAGE_TYPES:
            errors.append(f"Invalid message_type for {message_id}.")
    return errors


def main() -> None:
    """Run validation and print the saved report."""
    report = evaluate_output()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
