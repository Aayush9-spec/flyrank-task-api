
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "http://127.0.0.1:8001/triage"
CASES_PATH = Path(__file__).with_name("cases.json")
PROMPT_VERSION = "triage-v2"


def evaluate_case(case):
    payload = json.dumps({"text": case["input"]}).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        expected = case["expected"]

        category_match = result.get("category") == expected["category"]
        urgency_match = result.get("urgency") == expected["urgency"]
        confidence_valid = (
            isinstance(result.get("confidence"), (int, float))
            and 0.0 <= result["confidence"] <= 1.0
        )
        reason_valid = (
            isinstance(result.get("reason"), str)
            and bool(result["reason"].strip())
        )

        passed = (
            category_match
            and urgency_match
            and confidence_valid
            and reason_valid
        )

        return {
            "id": case["id"],
            "passed": passed,
            "expected": expected,
            "actual": {
                "category": result.get("category"),
                "urgency": result.get("urgency"),
            },
            "confidence": result.get("confidence"),
        }

    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {
            "id": case["id"],
            "passed": False,
            "error": str(error),
        }


def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    print(f"Prompt version: {PROMPT_VERSION}")
    print(f"API endpoint: {API_URL}")
    print(f"Total test cases: {len(cases)}")
    print("-" * 55)

    results = [evaluate_case(case) for case in cases]
    passed = sum(result["passed"] for result in results)
    total = len(results)
    score = (passed / total * 100) if total else 0

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status}: {result['id']}")

        if not result["passed"]:
            print(json.dumps(result, indent=2))

    print("-" * 55)
    print(f"Key-field match rate: {passed}/{total} ({score:.1f}%)")
    print(f"Failures: {total - passed}")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
