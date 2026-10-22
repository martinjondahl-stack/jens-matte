#!/usr/bin/env python3
"""Independent semantic audit for the generated JENS MATTE question bank.

The JavaScript validator checks schema and distribution. This audit adds checks
for mathematically equivalent answer choices, selected content formulas, visual
consistency, and a few Norwegian-language quality traps that are easy to miss in
large generated banks.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "data" / "questions.json"
AUDIT_PATH = ROOT / "data" / "question-bank-audit.json"


def decimal_nb(text: str) -> Decimal:
    return Decimal(text.replace(" ", "").replace(",", "."))


def option_value(text: str) -> tuple[str, Any, str] | None:
    """Normalize common numeric answers while keeping units distinct."""
    value = text.strip().replace("−", "-")
    mixed = re.fullmatch(r"(-?\d+)\s+(\d+)\s*/\s*(\d+)(.*)", value)
    if mixed:
        whole, numerator, denominator, suffix = mixed.groups()
        frac = Fraction(abs(int(whole)) * int(denominator) + int(numerator), int(denominator))
        if int(whole) < 0:
            frac = -frac
        return ("number", frac, suffix.strip())
    fraction = re.fullmatch(r"(-?\d+)\s*/\s*(\d+)(.*)", value)
    if fraction:
        numerator, denominator, suffix = fraction.groups()
        return ("number", Fraction(int(numerator), int(denominator)), suffix.strip())
    number = re.fullmatch(r"(-?\d+(?:,\d+)?)(.*)", value)
    if number:
        raw, suffix = number.groups()
        return ("number", decimal_nb(raw), suffix.strip())
    return None


def correct_text(question: dict[str, Any]) -> str:
    return next(option["text"] for option in question["options"] if option["id"] == question["correctOption"])


def nb(value: Decimal, places: int = 1) -> str:
    quantum = Decimal("1") if places == 0 else Decimal("1." + "0" * places)
    result = value.quantize(quantum, rounding=ROUND_HALF_UP)
    formatted = format(result, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted.replace(".", ",")


def main() -> None:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    questions = bank["questions"]
    errors: list[str] = []
    warnings: list[str] = []

    banned_fragments = {
        "1 røde": "Use singular '1 rød'.",
        "1 blåe": "Use singular '1 blå'.",
        "Første halvdel går i": "Use natural wording for travel speed.",
        "Til kinoen kjøpes": "Use a natural ticket context.",
    }

    for question in questions:
        qid = question["id"]
        prompt = question["prompt"]
        answer = correct_text(question)

        for fragment, message in banned_fragments.items():
            if fragment in prompt:
                errors.append(f"{qid}: {message}")

        # Four differently written alternatives must also represent four distinct values.
        normalized: list[tuple[str, str, tuple[str, Any, str] | None]] = [
            (option["id"], option["text"], option_value(option["text"]))
            for option in question["options"]
        ]
        for index, first in enumerate(normalized):
            for second in normalized[index + 1 :]:
                if first[2] is not None and first[2] == second[2]:
                    errors.append(
                        f"{qid}: semantically duplicate options {first[0]}={first[1]!r} and {second[0]}={second[1]!r}"
                    )

        for option in question["options"]:
            if option["id"] != question["correctOption"] and len(option["feedback"].strip()) < 18:
                warnings.append(f"{qid}/{option['id']}: very short targeted feedback")

        if question["type"] == "challenge" and len(question["explanation"]["steps"]) < 2:
            errors.append(f"{qid}: challenge needs at least two explanation steps")

        # Stated pi approximation must match the keyed answer.
        if "Bruk π ≈ 3,14" in prompt:
            radius_match = re.search(r"radius (\d+(?:,\d+)?) cm", prompt)
            diameter_match = re.search(r"diameter (\d+(?:,\d+)?) cm", prompt)
            pi = Decimal("3.14")
            if "omkretsen" in prompt and diameter_match:
                expected = pi * decimal_nb(diameter_match.group(1))
                expected_text = f"{nb(expected, 1)} cm"
            elif "arealet" in prompt and radius_match:
                radius = decimal_nb(radius_match.group(1))
                expected = pi * radius * radius
                expected_text = f"{nb(expected, 1)} cm²"
            else:
                errors.append(f"{qid}: could not parse circle task")
                expected_text = answer
            if answer != expected_text:
                errors.append(f"{qid}: circle answer {answer!r}, expected {expected_text!r} with pi=3.14")

        # Probability bag text and visual counts must agree.
        visual = question.get("visual") or {}
        if visual.get("type") == "probabilityBag":
            red = int(visual["red"])
            blue = int(visual["blue"])
            expected = Fraction(red, red + blue)
            parsed = option_value(answer)
            if not parsed or parsed[1] != expected or parsed[2]:
                errors.append(f"{qid}: probability answer {answer!r} does not match {red}/{red + blue}")
            if red == 1 and "1 rød" not in prompt:
                errors.append(f"{qid}: singular red-ball grammar is wrong")
            if blue == 1 and "1 blå" not in prompt:
                errors.append(f"{qid}: singular blue-ball grammar is wrong")

        # Inequality number-line metadata must match the selected solution.
        if question["skill"] == "ulikheter":
            relation = re.fullmatch(r"x\s*([<>]=?|[≤≥])\s*(-?\d+(?:,\d+)?)", answer)
            if not relation:
                errors.append(f"{qid}: could not parse inequality answer {answer!r}")
            else:
                symbol, raw_boundary = relation.groups()
                expected_direction = "left" if symbol in {"<", "≤"} else "right"
                expected_closed = symbol in {"≤", "≥"}
                if visual.get("type") != "numberLine":
                    errors.append(f"{qid}: inequality is missing number-line visual")
                if visual.get("direction") != expected_direction:
                    errors.append(f"{qid}: number-line direction does not match {answer}")
                if bool(visual.get("closed")) != expected_closed:
                    errors.append(f"{qid}: open/closed endpoint does not match {answer}")
                if Decimal(str(visual.get("boundary"))) != decimal_nb(raw_boundary):
                    errors.append(f"{qid}: number-line boundary does not match {answer}")

        # Two-stage travel tasks in this bank are intentionally exact to the minute.
        if question["skill"] == "fart og tid i flere etapper":
            match = re.search(
                r"En tur er (\d+) km.*?i (\d+) km/t.*?i (\d+) km/t",
                prompt,
            )
            if not match:
                errors.append(f"{qid}: could not parse two-stage trip")
            else:
                total, speed_a, speed_b = map(Decimal, match.groups())
                minutes = total / Decimal(2) / speed_a * Decimal(60) + total / Decimal(2) / speed_b * Decimal(60)
                if minutes != minutes.to_integral_value():
                    errors.append(f"{qid}: trip does not produce an exact number of minutes")
                if answer != f"{int(minutes)} min":
                    errors.append(f"{qid}: trip answer {answer!r}, expected {int(minutes)} min")

    report = {
        "bankVersion": bank.get("version"),
        "questionsAudited": len(questions),
        "semanticDuplicateChecks": True,
        "circleFormulaChecks": True,
        "probabilityChecks": True,
        "inequalityVisualChecks": True,
        "twoStageTravelChecks": True,
        "errors": errors,
        "warnings": warnings,
    }
    AUDIT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print(f"Semantic audit OK: {len(questions)} questions; {len(warnings)} non-blocking warnings.")


if __name__ == "__main__":
    main()
