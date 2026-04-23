from __future__ import annotations

import json
from pathlib import Path
import sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonebook.bot import resolve_phonebook_query
from phonebook.logging_config import configure_logging


def load_cases(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def main() -> None:
    configure_logging()
    eval_path = ROOT / "eval" / "phonebook_queries.jsonl"
    cases = load_cases(eval_path)

    top1_ok = 0
    top3_ok = 0
    no_answer_ok = 0
    failures: list[str] = []
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"cases": 0, "top1_ok": 0, "top3_ok": 0, "no_answer_cases": 0, "no_answer_ok": 0})
    by_status: dict[str, int] = defaultdict(int)

    for case in cases:
        decision = resolve_phonebook_query(case["query"], limit=3)
        results = decision.results
        parsed = decision.parsed_query
        result_ids = [row["id_phone_directory"] for row in results]
        expected_ids = case.get("expected_ids", [])
        expect_none = case.get("expect_none", False)
        category = case.get("category", "uncategorized")
        by_category[category]["cases"] += 1
        by_status[decision.status] += 1

        if expect_none:
            by_category[category]["no_answer_cases"] += 1
            if not result_ids:
                no_answer_ok += 1
                by_category[category]["no_answer_ok"] += 1
            else:
                failures.append(
                    f"{case['id']}: expected none, got {result_ids} for query '{case['query']}'"
                )
            continue

        if result_ids and result_ids[0] in expected_ids:
            top1_ok += 1
            by_category[category]["top1_ok"] += 1
        else:
            failures.append(
                f"{case['id']}: top1 miss, got {result_ids[:1]} expected one of {expected_ids}; parsed={parsed}"
            )

        if any(item in expected_ids for item in result_ids[:3]):
            top3_ok += 1
            by_category[category]["top3_ok"] += 1

    ranked_total = sum(1 for case in cases if not case.get("expect_none", False))
    no_answer_total = sum(1 for case in cases if case.get("expect_none", False))

    print(f"Cases total: {len(cases)}")
    print(f"Top-1 accuracy: {top1_ok}/{ranked_total} = {top1_ok / ranked_total:.3f}")
    print(f"Top-3 accuracy: {top3_ok}/{ranked_total} = {top3_ok / ranked_total:.3f}")
    if no_answer_total:
        print(f"No-answer accuracy: {no_answer_ok}/{no_answer_total} = {no_answer_ok / no_answer_total:.3f}")

    print("\nBy category:")
    for category in sorted(by_category):
        stats = by_category[category]
        ranked_cases = stats["cases"] - stats["no_answer_cases"]
        line = f"- {category}: cases={stats['cases']}"
        if ranked_cases:
            line += f", top1={stats['top1_ok']}/{ranked_cases}, top3={stats['top3_ok']}/{ranked_cases}"
        if stats["no_answer_cases"]:
            line += f", no-answer={stats['no_answer_ok']}/{stats['no_answer_cases']}"
        print(line)

    print("\nBy status:")
    for status in sorted(by_status):
        print(f"- {status}: {by_status[status]}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("\nAll eval cases passed.")


if __name__ == "__main__":
    main()
