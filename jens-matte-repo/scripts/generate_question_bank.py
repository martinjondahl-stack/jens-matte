#!/usr/bin/env python3
"""Generate the JENS MATTE question bank.

The bank is deterministic and intended to be reviewed in Git. Every question has
four options, one correct answer, a worked explanation, feedback for each wrong
choice, curriculum metadata, and (where useful) a small SVG-friendly visual spec.
"""
from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "questions.json"
REPORT = ROOT / "data" / "question-bank-report.json"
SEED = 20261020
RNG = random.Random(SEED)

TOPIC_TARGETS = {
    "Tall og regnearter": 70,
    "Brøk": 75,
    "Desimaltall": 50,
    "Prosent": 55,
    "Algebra og mønster": 50,
    "Geometri": 45,
    "Måling": 35,
    "Statistikk og sannsynlighet": 35,
    "Økonomi": 30,
    "Problemløsing": 55,
}

TOPIC_CODES = {
    "Tall og regnearter": "TAL",
    "Brøk": "BRO",
    "Desimaltall": "DES",
    "Prosent": "PRO",
    "Algebra og mønster": "ALG",
    "Geometri": "GEO",
    "Måling": "MAL",
    "Statistikk og sannsynlighet": "STA",
    "Økonomi": "EKO",
    "Problemløsing": "PRB",
}

OPTION_IDS = ["A", "B", "C", "D"]


def nb_num(value: float | int | Decimal, max_decimals: int = 2) -> str:
    """Norwegian number formatting without thousands separators."""
    if isinstance(value, Decimal):
        d = value
    else:
        d = Decimal(str(value))
    quantum = Decimal("1") if max_decimals == 0 else Decimal("1." + "0" * max_decimals)
    d = d.quantize(quantum, rounding=ROUND_HALF_UP)
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


def frac_text(value: Fraction | tuple[int, int]) -> str:
    if isinstance(value, tuple):
        value = Fraction(*value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def money(value: float | int | Decimal) -> str:
    return f"{nb_num(value, 2)} kr"


def with_unit(value: float | int | Decimal, unit: str, max_decimals: int = 2) -> str:
    return f"{nb_num(value, max_decimals)} {unit}"


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def feedback_generic(correct: str) -> str:
    return f"Se på regnestykket én gang til. Det riktige svaret er {correct}."


def fallback_distractors(correct: str) -> list[str]:
    """Create plausible emergency distractors when a hand-authored one collides."""
    result: list[str] = []
    frac = re.fullmatch(r"(-?\d+)/(\d+)", correct)
    if frac:
        n, d = map(int, frac.groups())
        result.extend([f"{n+1}/{d}", f"{max(0, n-1)}/{d}", f"{n}/{d+1}", f"{d}/{n or 1}"])
    coord = re.fullmatch(r"\((-?\d+),\s*(-?\d+)\)", correct)
    if coord:
        x, y = map(int, coord.groups())
        result.extend([f"({y}, {x})", f"({-x}, {y})", f"({x}, {-y})", f"({-x}, {-y})"])
    num = re.match(r"^(-?\d+(?:,\d+)?)(.*)$", correct)
    if num:
        raw, suffix = num.groups()
        value = Decimal(raw.replace(",", "."))
        step = Decimal("0.1") if "," in raw else Decimal("1")
        for delta in (step, -step, step * 2, step * 10):
            candidate = nb_num(value + delta, 3 if "," in raw else 0) + suffix
            result.append(candidate)
    result.extend(["Ingen av disse", "Kan ikke bestemmes", "0", "1"])
    return unique(result)


@dataclass
class Wrong:
    text: str
    feedback: str


class BankBuilder:
    def __init__(self) -> None:
        self.questions: list[dict[str, Any]] = []
        self.topic_counts: Counter[str] = Counter()

    def add(
        self,
        *,
        topic: str,
        grade: int,
        level: int,
        skill: str,
        qtype: str,
        prompt: str,
        correct: str,
        wrongs: list[Wrong],
        explanation_steps: list[str],
        takeaway: str,
        visual: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        hint: str | None = None,
    ) -> None:
        assert topic in TOPIC_TARGETS, topic
        assert grade in (5, 6, 7)
        assert 1 <= level <= 10
        assert qtype in ("quick", "standard", "challenge")
        wrong_map: dict[str, str] = {}
        for wrong in wrongs:
            if wrong.text != correct and wrong.text not in wrong_map:
                wrong_map[wrong.text] = wrong.feedback
        if len(wrong_map) < 3:
            for candidate in fallback_distractors(correct):
                if candidate != correct and candidate not in wrong_map:
                    wrong_map[candidate] = feedback_generic(correct)
                if len(wrong_map) >= 3:
                    break
        if len(wrong_map) < 3:
            raise ValueError(f"Not enough unique distractors for: {prompt!r}; {list(wrong_map)}")
        chosen = list(wrong_map.items())[:3]
        option_rows = [(correct, "")] + chosen
        local_rng = random.Random(f"{SEED}:{topic}:{prompt}:{len(self.questions)}")
        local_rng.shuffle(option_rows)
        options = []
        correct_option = ""
        for idx, (text, feedback) in enumerate(option_rows):
            oid = OPTION_IDS[idx]
            if text == correct:
                correct_option = oid
            options.append({"id": oid, "text": text, "feedback": feedback})
        base_xp = {"quick": 12, "standard": 20, "challenge": 35}[qtype]
        xp = base_xp + level * {"quick": 2, "standard": 3, "challenge": 5}[qtype]
        number = self.topic_counts[topic] + 1
        qid = f"JM-{TOPIC_CODES[topic]}-{number:03d}"
        self.topic_counts[topic] += 1
        self.questions.append(
            {
                "id": qid,
                "grade": grade,
                "level": level,
                "topic": topic,
                "skill": skill,
                "type": qtype,
                "prompt": prompt,
                "hint": hint or default_hint(topic, skill),
                "options": options,
                "correctOption": correct_option,
                "explanation": {
                    "summary": takeaway,
                    "steps": explanation_steps,
                    "takeaway": takeaway,
                },
                "xp": xp,
                "visual": visual,
                "tags": tags or [],
            }
        )

    def ensure_targets(self) -> None:
        for topic, target in TOPIC_TARGETS.items():
            actual = self.topic_counts[topic]
            if actual != target:
                raise AssertionError(f"{topic}: expected {target}, got {actual}")
        if len(self.questions) != 500:
            raise AssertionError(f"Expected 500 questions, got {len(self.questions)}")




def default_hint(topic: str, skill: str) -> str:
    """A short strategy cue without revealing the answer."""
    exact = {
        "addisjon og subtraksjon": "Still tallene under hverandre, eller del dem opp i hundrere, tiere og enere.",
        "multiplikasjon og divisjon": "Se om du kan dele opp et tall i enklere deler før du regner.",
        "regnerekkefølge": "Regn parenteser først, så gange og dele, og til slutt pluss og minus.",
        "negative tall": "Tegn gjerne en tallinje og følg bevegelsen steg for steg.",
        "avrunding og overslag": "Se på sifferet rett til høyre for plassen du skal runde av til.",
        "faktorer": "Prøv hvilke hele tall som går opp uten rest.",
        "primtall": "Et primtall kan bare deles på 1 og seg selv uten rest.",
        "potenser og plassverdi": "Skriv potensen som gjentatt multiplikasjon, eller se på plassverdien.",
        "likeverdige brøker": "Gang eller del teller og nevner med det samme tallet.",
        "sammenligne brøker": "Finn en felles nevner, eller sammenlign hvor stor del av en hel hver brøk er.",
        "brøk av mengde": "Del mengden på nevneren først, og gang deretter med telleren.",
        "finne helheten fra en brøk": "Finn først hvor mye én brøkdel er verdt.",
        "brøk i tekstoppgaver": "Skriv hele mengden som en brøk med samme nevner før du regner.",
        "blandet tall og uekte brøk": "Tell hele deler først, og gjør resten om til samme nevner.",
        "plassverdi": "Se hvilken plass hvert siffer står på i tallet.",
        "gange og dele med 10, 100 og 1000": "Følg hvordan sifrene flytter plass når tallet ganges eller deles.",
        "sammenligne og avrunde desimaltall": "Sammenlign tideler først, deretter hundredeler og tusendeler.",
        "multiplikasjon med desimaltall": "Regn uten komma først, og plasser kommaet til slutt.",
        "prosent av en mengde": "Finn gjerne 10 %, 5 % eller 1 % først.",
        "rabatt": "Finn først hvor mange kroner rabatten er, og trekk den fra førprisen.",
        "brøk, desimaltall og prosent": "Tenk på prosent som hundredeler: 25 % = 25/100.",
        "finne helheten fra prosent": "Finn hva 1 % er verdt, og gang opp til 100 %.",
        "prosentvis økning og nedgang": "Finn endringen først, og legg den til eller trekk den fra startverdien.",
        "prosentpoeng og andeler": "Prosentpoeng er forskjellen mellom to prosenttall.",
        "tallmønster": "Se på forskjellen mellom to nabotall og sjekk om den gjentar seg.",
        "ettstegsligninger": "Gjør motsatt regneoperasjon på begge sider av likhetstegnet.",
        "tostegsligninger": "Fjern først tallet som er lagt til eller trukket fra, og del deretter.",
        "sette inn verdi i uttrykk": "Bytt ut bokstaven med tallet, og følg regnerekkefølgen.",
        "funksjonsregel": "Sammenlign inn- og utverdiene for å finne samme regel i hver rad.",
        "ulikheter": "Prøv hvert svar og sjekk om ulikhetstegnet blir sant.",
        "areal av rektangel": "Areal finner du ved å gange lengde med bredde.",
        "omkrets av rektangel": "Omkrets er hele veien rundt figuren.",
        "areal av trekant": "Trekantens areal er grunnlinje · høyde ÷ 2.",
        "vinkler": "Bruk at en rett linje er 180°, og at trekantvinkler summerer til 180°.",
        "koordinater og speiling": "Les x-koordinaten først og y-koordinaten etterpå.",
        "radius og diameter": "Diameteren er dobbelt så lang som radiusen.",
        "sirkelens omkrets": "Bruk omkrets ≈ π · diameter.",
        "sirkelens areal": "Bruk areal ≈ π · radius · radius.",
        "sammensatte figurer": "Del figuren i enklere rektangler og legg delene sammen.",
        "omgjøring av måleenheter": "Skriv en liten omgjøringstabell før du flytter kommaet.",
        "tid og varighet": "Del tiden ved hele timer dersom det gjør regningen enklere.",
        "volum": "Volum av et rett prisme er lengde · bredde · høyde.",
        "målestokk": "Finn hva 1 cm på kartet tilsvarer i virkeligheten.",
        "fart": "Bruk sammenhengen fart = strekning ÷ tid.",
        "lese diagram": "Les av akser, etiketter og skala før du sammenligner søylene.",
        "gjennomsnittet": "Legg sammen alle verdiene og del på hvor mange verdier det er.",
        "medianen": "Sorter tallene og finn verdien i midten.",
        "typetallet": "Finn tallet som forekommer flest ganger.",
        "variasjonsbredden": "Trekk den minste verdien fra den største.",
        "enkel sannsynlighet": "Tell gunstige utfall og del på alle mulige utfall.",
        "sammensatt og eksperimentell sannsynlighet": "Finn sannsynligheten for hvert trinn før du kombinerer dem.",
        "vekslepenger": "Trekk totalprisen fra beløpet som ble betalt.",
        "totalpris": "Finn prisen for hver varetype før du legger sammen.",
        "budsjett": "Legg sammen utgiftene først, og trekk dem fra pengene du har.",
        "enkel rente": "Finn prosenten av startbeløpet og legg renten til.",
        "sammenligne tilbud": "Regn pris per vare for begge tilbudene.",
        "flerstegsregning": "Skriv ett delregnestykke for hver opplysning før du finner totalen.",
        "forhold og oppskrifter": "Finn hvor mange ganger antall porsjoner endres.",
        "fart og tid i flere etapper": "Finn tiden for hver etappe separat før du legger sammen.",
        "finne helhet fra rest": "Finn hvilken brøkdel som er igjen, og bruk den til å finne hele mengden.",
        "areal i praktisk situasjon": "Finn først arealet av hele flaten og deretter arealet av én del.",
        "systematisk opptelling": "Lag et rutenett eller gang antall valg i de to gruppene.",
        "avansert brøkproblem": "Finn først hvor stor brøkdel endringen utgjør.",
    }
    if skill in exact:
        return exact[skill]
    if "brøk" in skill or topic == "Brøk":
        return "Tegn en enkel brøkmodell og finn en felles helhet."
    if topic == "Prosent":
        return "Knytt prosenttallet til 100 %, 10 % eller 1 %."
    if topic == "Geometri":
        return "Marker målene i figuren og velg riktig formel."
    return "Finn ut hva spørsmålet ber om, og skriv ett regnesteg om gangen."

def wrong(text: str, feedback: str) -> Wrong:
    return Wrong(text, feedback)


def generic_wrongs(values: Iterable[str], correct: str) -> list[Wrong]:
    return [wrong(v, feedback_generic(correct)) for v in values if v != correct]


def grade_level(level: int) -> int:
    if level <= 4:
        return 5
    if level <= 6:
        return 6
    return 7


def add_tall(builder: BankBuilder) -> None:
    # 10: multi-digit add/subtract
    pairs = [(348, 276), (725, 189), (1460, 785), (2384, 1679), (5200, 2875),
             (907, 468), (1305, 678), (4302, 1956), (10000, 3768), (6543, 2897)]
    for i, (a, b) in enumerate(pairs):
        subtract = i % 2 == 1
        level = 1 + i // 3
        if subtract:
            if a < b:
                a, b = b, a
            ans = a - b
            prompt = f"Hva er {a} − {b}?"
            ws = [
                wrong(str(a + b), "Du la sammen tallene. Her skal vi trekke fra."),
                wrong(str(abs(ans - 100)), "Sjekk vekslingen mellom hundrere og tiere."),
                wrong(str(ans + 10), "Sjekk ener- og tierplassen."),
            ]
            steps = [f"Still opp {a} − {b} med ener under ener.", f"Trekk fra fra høyre mot venstre.", f"Resultatet blir {ans}."]
        else:
            ans = a + b
            prompt = f"Hva er {a} + {b}?"
            ws = [
                wrong(str(abs(a - b)), "Du trakk fra. Her skal tallene legges sammen."),
                wrong(str(ans - 100), "Husk å ta med hundreren som kommer ved veksling."),
                wrong(str(ans + 10), "Sjekk tierplassen en gang til."),
            ]
            steps = [f"Legg sammen enerne, så tierne og hundrerne.", f"Ta med eventuell veksling.", f"Summen er {ans}."]
        builder.add(topic="Tall og regnearter", grade=grade_level(level), level=level, skill="addisjon og subtraksjon",
                    qtype="quick", prompt=prompt, correct=str(ans), wrongs=ws, explanation_steps=steps,
                    takeaway=f"Svaret er {ans}.", tags=["hoderegning", "fire regnearter"])

    # 10: multiplication and division
    cases = [(18, 7), (24, 6), (35, 8), (144, 12), (225, 15), (32, 25), (84, 14), (125, 16), (252, 18), (420, 21)]
    for i, (a, b) in enumerate(cases):
        divide = i % 2 == 1
        level = 2 + i // 3
        if divide:
            product = a if a % b == 0 else a * b
            divisor = b
            ans = product // divisor
            prompt = f"Hva er {product} ÷ {divisor}?"
            ws = [
                wrong(str(product - divisor), "Du trakk fra én gang. Divisjon spør hvor mange ganger divisoren går opp i tallet."),
                wrong(str(ans + 1), "Prøv å gange svaret ditt med divisoren for å kontrollere."),
                wrong(str(divisor), "Divisoren er tallet vi deler på, ikke alltid svaret."),
            ]
            steps = [f"Finn tallet som ganget med {divisor} blir {product}.", f"{divisor} × {ans} = {product}.", f"Derfor er svaret {ans}."]
        else:
            ans = a * b
            prompt = f"Hva er {a} · {b}?"
            ws = [
                wrong(str(a + b), "Du la sammen faktorene. Multiplikasjon betyr gjentatt addisjon."),
                wrong(str(ans - a), f"Dette tilsvarer bare {b-1} grupper med {a}."),
                wrong(str(ans + b), "Du har lagt til én gruppe for mye."),
            ]
            steps = [f"Del gjerne {b} opp i enklere deler.", f"Regn {a} × {b}.", f"Produktet er {ans}."]
        builder.add(topic="Tall og regnearter", grade=grade_level(level), level=level, skill="multiplikasjon og divisjon",
                    qtype="quick", prompt=prompt, correct=str(ans), wrongs=ws, explanation_steps=steps,
                    takeaway=f"Svaret er {ans}.", tags=["hoderegning", "fire regnearter"])

    # 10: order of operations, including parentheses
    order_cases = [
        {
            "prompt": "Hva er 6 + 4 · 3?", "answer": 18, "level": 4,
            "wrongs": [(30, "Du regnet fra venstre mot høyre. Multiplikasjon skal tas før addisjon."),
                       (22, "Du ser ut til å ha lagt til én ekstra 4-er."),
                       (16, "Kontroller produktet 4 · 3.")],
            "steps": ["Multiplikasjon regnes før addisjon: 4 · 3 = 12.", "Deretter: 6 + 12 = 18."],
        },
        {
            "prompt": "Hva er 36 ÷ 6 + 4?", "answer": 10, "level": 4,
            "wrongs": [(3.6, "Du samlet 6 + 4 som om det sto en parentes der."),
                       (24, "Du ser ut til å ha ganget i stedet for å dele."),
                       (6, "Du stoppet etter divisjonen og glemte å legge til 4.")],
            "steps": ["Divisjon regnes før addisjon: 36 ÷ 6 = 6.", "Deretter: 6 + 4 = 10."],
        },
        {
            "prompt": "Hva er 7 · (8 − 5)?", "answer": 21, "level": 5,
            "wrongs": [(51, "Du ignorerte parentesen. Det som står i parentes, skal regnes først."),
                       (35, "Du ganget 7 med 5, men parentesen er 8 − 5."),
                       (10, "Du trakk fra faktorene i stedet for å multiplisere etter parentesen.")],
            "steps": ["Regn parentesen først: 8 − 5 = 3.", "Deretter: 7 · 3 = 21."],
        },
        {
            "prompt": "Hva er (18 + 6) ÷ 3?", "answer": 8, "level": 5,
            "wrongs": [(20, "Du tok divisjonen før parentesen. Parentesen skal regnes først."),
                       (24, "Dette er verdien i parentesen, men du må også dele på 3."),
                       (6, "Du delte bare 18 på 3 og glemte 6 i parentesen.")],
            "steps": ["Regn parentesen først: 18 + 6 = 24.", "Deretter: 24 ÷ 3 = 8."],
        },
        {
            "prompt": "Hva er 48 ÷ (4 · 3)?", "answer": 4, "level": 6,
            "wrongs": [(36, "Du regnet 48 ÷ 4 · 3 uten å behandle parentesen som én divisor."),
                       (12, "Dette er verdien i parentesen, ikke hele svaret."),
                       (16, "Du delte 48 på 3, men divisoren er 4 · 3.")],
            "steps": ["Regn parentesen først: 4 · 3 = 12.", "Deretter: 48 ÷ 12 = 4."],
        },
        {
            "prompt": "Hva er 5 + 24 ÷ (3 · 2)?", "answer": 9, "level": 6,
            "wrongs": [(14.5, "Du samlet 5 + 24 før divisjonen. Regn parentes og divisjon først."),
                       (13, "Du delte 24 bare på 3. Hele parentesen er 3 · 2."),
                       (4, "Dette er bare 24 ÷ 6. Du må også legge til 5.")],
            "steps": ["Parentesen først: 3 · 2 = 6.", "Så divisjon: 24 ÷ 6 = 4.", "Til slutt: 5 + 4 = 9."],
        },
        {
            "prompt": "Hva er (14 − 6) · 5?", "answer": 40, "level": 7,
            "wrongs": [(-16, "Du regnet multiplikasjonen før parentesen."),
                       (8, "Dette er bare svaret i parentesen."),
                       (34, "Du ser ut til å ha trukket fra 6 etter én multiplikasjon, uten å bruke parentesen riktig.")],
            "steps": ["Parentesen først: 14 − 6 = 8.", "Deretter: 8 · 5 = 40."],
        },
        {
            "prompt": "Hva er 72 ÷ (9 − 3)?", "answer": 12, "level": 7,
            "wrongs": [(5, "Du regnet 72 ÷ 9 − 3 og hoppet over parentesen."),
                       (6, "Dette er verdien i parentesen, ikke hele svaret."),
                       (24, "Du delte 72 på 3, men divisoren er 9 − 3.")],
            "steps": ["Parentesen først: 9 − 3 = 6.", "Deretter: 72 ÷ 6 = 12."],
        },
        {
            "prompt": "Hva er 3 · (12 + 8) − 10?", "answer": 50, "level": 8,
            "wrongs": [(34, "Du behandlet uttrykket som 3 · 12 + 8 − 10 og ignorerte parentesen."),
                       (60, "Du stoppet etter multiplikasjonen og glemte å trekke fra 10."),
                       (23, "Du la sammen inni parentesen, men glemte å gange hele parentesen med 3.")],
            "steps": ["Parentesen først: 12 + 8 = 20.", "Så multiplikasjon: 3 · 20 = 60.", "Til slutt: 60 − 10 = 50."],
        },
        {
            "prompt": "Hva er 100 − (18 + 7) · 3?", "answer": 25, "level": 9,
            "wrongs": [(225, "Du trakk fra parentesen før du ganget. Multiplikasjonen må gjøres før den siste subtraksjonen."),
                       (75, "Dette er produktet (18 + 7) · 3, men det skal trekkes fra 100."),
                       (229, "Du brukte bare 18 i produktet og lot 7 stå utenfor parentesen.")],
            "steps": ["Parentesen først: 18 + 7 = 25.", "Så multiplikasjon: 25 · 3 = 75.", "Til slutt: 100 − 75 = 25."],
        },
    ]
    for case in order_cases:
        correct = nb_num(case["answer"], 1)
        ws = [wrong(nb_num(value, 1), feedback) for value, feedback in case["wrongs"]]
        builder.add(
            topic="Tall og regnearter", grade=grade_level(case["level"]), level=case["level"],
            skill="regnerekkefølge", qtype="challenge" if case["level"] >= 8 else "standard",
            prompt=case["prompt"], correct=correct, wrongs=ws, explanation_steps=case["steps"],
            takeaway=f"Riktig verdi er {correct}.", tags=["regnerekkefølge", "parenteser"],
        )

    # 10: negative numbers, all visual number lines
    neg_cases = [(-4, 9), (3, -8), (-7, -5), (-12, 7), (5, -13), (-6, 14), (-15, 9), (2, -11), (-9, -4), (-18, 25)]
    for i, (start, change) in enumerate(neg_cases):
        ans = start + change
        verb = "stiger" if change > 0 else "synker"
        amount = abs(change)
        prompt = f"Temperaturen er {start} °C og {verb} {amount} grader. Hva blir temperaturen?"
        level = 6 + i // 3
        ws = [
            wrong(with_unit(start - change, "°C", 0), "Du gikk motsatt vei på tallinja."),
            wrong(with_unit(abs(start) + abs(change), "°C", 0), "Fortegnene avgjør om du skal gå mot høyre eller venstre."),
            wrong(with_unit(-ans, "°C", 0), "Du fant avstanden, men fortegnet ble motsatt."),
        ]
        steps = [f"Start på {start} på tallinja.", f"{verb.capitalize()} betyr at du går {'mot høyre' if change>0 else 'mot venstre'} {amount} steg.", f"Du lander på {ans} °C."]
        visual = {"type": "numberLine", "min": min(-20, start, ans)-2, "max": max(20, start, ans)+2, "start": start, "end": ans}
        builder.add(topic="Tall og regnearter", grade=7, level=level, skill="negative tall",
                    qtype="standard", prompt=prompt, correct=with_unit(ans, "°C", 0), wrongs=ws,
                    explanation_steps=steps, takeaway=f"Den nye temperaturen er {ans} °C.", visual=visual,
                    tags=["tallinje", "negative tall"])

    # 10: factors, primes and divisibility
    nums = [24, 36, 45, 56, 63, 72, 84, 90, 96, 105]
    for i, n in enumerate(nums):
        level = 4 + i // 3
        if i % 2 == 0:
            candidates = [2, 3, 5, 7]
            divisors = [d for d in candidates if n % d == 0]
            non = [d for d in candidates if n % d != 0]
            answer = non[0] if non else 11
            prompt = f"Hvilket tall er ikke en faktor i {n}?"
            ws = [wrong(str(d), f"{n} ÷ {d} er et helt tall, så {d} er en faktor.") for d in divisors[:3]]
            while len(ws) < 3:
                d = [x for x in range(2, 12) if n % x == 0 and str(x) not in [w.text for w in ws]][0]
                ws.append(wrong(str(d), f"{n} kan deles på {d} uten rest."))
            steps = [f"En faktor deler {n} uten rest.", f"Prøv kandidatene én etter én.", f"{n} kan ikke deles på {answer} uten rest."]
            correct = str(answer)
            skill = "faktorer"
        else:
            primes = [2, 3, 5, 7, 11, 13, 17, 19]
            correct_prime = primes[(i * 2) % len(primes)]
            composites = [n, n+2 if (n+2) % 2 == 0 else n+3, 21]
            prompt = "Hvilket av tallene er et primtall?"
            correct = str(correct_prime)
            ws = [wrong(str(v), f"{v} har flere faktorer enn 1 og seg selv.") for v in unique(map(str, composites))]
            ws = [Wrong(w.text, w.feedback) for w in ws]
            while len(ws) < 3:
                v = 27 + len(ws)*6
                ws.append(wrong(str(v), f"{v} kan deles på 3."))
            steps = ["Et primtall har nøyaktig to positive faktorer: 1 og seg selv.", f"{correct_prime} kan ikke deles uten rest på andre positive heltall."]
            skill = "primtall"
        builder.add(topic="Tall og regnearter", grade=grade_level(level), level=level, skill=skill,
                    qtype="standard", prompt=prompt, correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"Riktig svar er {correct}.", tags=["tallforståelse"])

    # 10: rounding and estimation
    round_cases = [(347, 10), (1264, 100), (7850, 1000), (49.6, 1), (8.47, 0.1),
                   (995, 100), (2501, 1000), (63.54, 1), (12.349, 0.1), (14949, 1000)]
    for i, (value, step) in enumerate(round_cases):
        if step >= 1:
            ans = int(math.floor((float(value) + step/2) / step) * step)
            place = {10: "nærmeste tier", 100: "nærmeste hundrer", 1000: "nærmeste tusen", 1: "nærmeste hele tall"}[step]
        else:
            ans = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            place = "nærmeste tidel"
        prompt = f"Rund {nb_num(value, 3)} av til {place}."
        level = 2 + i // 3
        correct = nb_num(ans, 1 if step < 1 else 0)
        low = Decimal(str(ans)) - Decimal(str(step))
        high = Decimal(str(ans)) + Decimal(str(step))
        ws = [
            wrong(nb_num(low, 1 if step < 1 else 0), "Du rundet ned. Se på sifferet til høyre for plassen du runder til."),
            wrong(nb_num(high, 1 if step < 1 else 0), "Du rundet ett hakk for langt opp."),
            wrong(nb_num(float(value), 3), "Dette er det opprinnelige tallet, ikke det avrundede."),
        ]
        steps = [f"Finn sifferet på plassen for {place}.", "Se på sifferet rett til høyre: 5 eller mer runder opp, ellers ned.", f"Resultatet er {correct}."]
        builder.add(topic="Tall og regnearter", grade=grade_level(level), level=level, skill="avrunding og overslag",
                    qtype="quick", prompt=prompt, correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"Avrundet verdi er {correct}.", tags=["avrunding"])

    # 10: powers and place value
    pow_cases = [(10, 3), (2, 5), (5, 3), (3, 4), (10, 5), (4, 3), (6, 2), (2, 8), (7, 2), (3, 5)]
    for i, (base, exp) in enumerate(pow_cases):
        ans = base ** exp
        level = 5 + i // 3
        prompt = f"Hva er {base}^{exp}?"
        ws = [
            wrong(str(base * exp), "Eksponenten betyr gjentatt multiplikasjon, ikke base ganger eksponent."),
            wrong(str(base ** max(1, exp-1)), "Du har brukt én faktor for lite."),
            wrong(str(ans + base), "Sjekk at du bare ganger basen med seg selv riktig antall ganger."),
        ]
        steps = [f"{base}^{exp} betyr at {base} skal være faktor {exp} ganger.", " · ".join([str(base)] * exp) + f" = {ans}."]
        builder.add(topic="Tall og regnearter", grade=grade_level(level), level=level, skill="potenser og plassverdi",
                    qtype="standard", prompt=prompt, correct=str(ans), wrongs=ws, explanation_steps=steps,
                    takeaway=f"{base}^{exp} = {ans}.", tags=["potenser"])


def add_brok(builder: BankBuilder) -> None:
    # 10: fraction of quantity
    cases = [(1, 3, 24), (2, 5, 35), (3, 4, 28), (5, 6, 42), (3, 8, 64),
             (7, 10, 90), (4, 9, 81), (5, 12, 96), (7, 15, 120), (11, 20, 200)]
    for i, (num, den, total) in enumerate(cases):
        ans = total * num // den
        level = 1 + i // 2
        correct = str(ans)
        ws = [
            wrong(str(total // den), f"Dette er bare 1/{den} av mengden. Du må gange med {num}."),
            wrong(str(total * den // num if total * den % num == 0 else total * den), "Du har byttet om på teller og nevner."),
            wrong(str(total - ans), "Dette er resten, ikke brøkdelen det spørres om."),
        ]
        steps = [f"Finn først 1/{den} av {total}: {total} ÷ {den} = {total//den}.", f"Gang så med {num}: {total//den} · {num} = {ans}."]
        visual = {"type": "fractionBar", "numerator": num, "denominator": den, "label": f"{num}/{den}"} if i < 6 else None
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="brøk av mengde", qtype="quick" if level < 4 else "standard",
                    prompt=f"Hva er {num}/{den} av {total}?", correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"{num}/{den} av {total} er {ans}.", visual=visual, tags=["brøk", "mengde"])

    # 10: compare fractions
    frac_sets = [
        [Fraction(1,2), Fraction(3,5), Fraction(5,8), Fraction(2,3)],
        [Fraction(3,4), Fraction(7,10), Fraction(5,6), Fraction(4,5)],
        [Fraction(2,7), Fraction(3,8), Fraction(4,9), Fraction(5,12)],
        [Fraction(7,8), Fraction(9,10), Fraction(11,12), Fraction(5,6)],
        [Fraction(4,5), Fraction(13,20), Fraction(3,4), Fraction(7,10)],
        [Fraction(5,9), Fraction(7,12), Fraction(3,5), Fraction(11,18)],
        [Fraction(2,3), Fraction(7,11), Fraction(5,8), Fraction(9,14)],
        [Fraction(11,15), Fraction(3,4), Fraction(7,10), Fraction(13,20)],
        [Fraction(5,6), Fraction(13,16), Fraction(4,5), Fraction(7,8)],
        [Fraction(9,20), Fraction(7,15), Fraction(1,2), Fraction(11,25)],
    ]
    for i, fs in enumerate(frac_sets):
        greatest = max(fs)
        level = 2 + i // 2
        correct = frac_text(greatest)
        ws = [wrong(frac_text(f), "Sammenlign ved å finne felles nevner eller gjøre brøkene om til desimaltall.") for f in fs if f != greatest]
        steps = ["Gjør brøkene om til like nevnere eller desimaltall.", f"{correct} har størst verdi av alternativene."]
        visual = {"type": "fractionCompare", "fractions": [frac_text(f) for f in fs]} if i < 5 else None
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="sammenligne brøker", qtype="standard",
                    prompt="Hvilken brøk er størst?", correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"{correct} er størst.", visual=visual, tags=["brøk", "sammenligning"])

    # 10: equivalent fractions
    cases2 = [(1,2,4), (2,3,9), (3,5,20), (4,7,21), (5,8,32), (7,10,50), (3,4,28), (5,6,42), (7,12,60), (11,15,75)]
    for i, (n, d, new_d) in enumerate(cases2):
        factor = new_d // d
        new_n = n * factor
        correct = f"{new_n}/{new_d}"
        level = 2 + i // 2
        ws = [
            wrong(f"{n}/{new_d}", "Når nevneren ganges, må telleren ganges med samme tall."),
            wrong(f"{new_n+factor}/{new_d}", "Telleren er ganget med feil faktor."),
            wrong(f"{new_d}/{new_n}", "Teller og nevner har blitt byttet om."),
        ]
        steps = [f"{d} må ganges med {factor} for å bli {new_d}.", f"Gang telleren med samme faktor: {n} · {factor} = {new_n}.", f"Dermed er brøken {correct}."]
        visual = {"type": "fractionBar", "numerator": n, "denominator": d, "label": f"{n}/{d}"} if i < 5 else None
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="likeverdige brøker", qtype="standard",
                    prompt=f"Hvilken brøk er like mye som {n}/{d} og har nevner {new_d}?", correct=correct, wrongs=ws,
                    explanation_steps=steps, takeaway=f"{n}/{d} = {correct}.", visual=visual, tags=["utvide brøk"])

    # 10: add/subtract same denominator
    cases3 = [(2,3,7,"+"), (5,2,9,"-"), (4,5,11,"+"), (9,4,12,"-"), (3,7,10,"+"),
              (11,5,14,"-"), (5,8,16,"+"), (13,7,18,"-"), (7,9,20,"+"), (17,8,24,"-")]
    for i, (a, b, d, op) in enumerate(cases3):
        result_n = a + b if op == "+" else a - b
        f = Fraction(result_n, d)
        correct = frac_text(f)
        level = 2 + i // 3
        wrong_den = d * 2
        ws = [
            wrong(f"{result_n}/{wrong_den}", "Nevneren skal ikke legges sammen når den allerede er lik."),
            wrong(frac_text(Fraction(abs(a-b) if op=='+' else a+b, d)), "Du brukte motsatt regneart på tellerne."),
            wrong(f"{result_n+1}/{d}", "Sjekk addisjonen eller subtraksjonen i telleren."),
        ]
        steps = [f"Nevneren er allerede lik: {d}.", f"Regn tellerne: {a} {op} {b} = {result_n}.", f"Forkort om mulig: svaret er {correct}."]
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="addisjon og subtraksjon med lik nevner",
                    qtype="quick", prompt=f"Hva er {a}/{d} {op} {b}/{d}?", correct=correct, wrongs=ws,
                    explanation_steps=steps, takeaway=f"Svaret er {correct}.", tags=["brøkregning"])

    # 10: unlike denominators
    cases4 = [(1,2,1,3,"+"), (3,4,1,6,"-"), (2,5,1,4,"+"), (5,6,1,3,"-"), (3,8,1,6,"+"),
              (7,10,1,4,"-"), (5,12,2,9,"+"), (11,15,1,6,"-"), (7,18,5,12,"+"), (13,20,3,8,"-")]
    for i, (a,b,c,d,op) in enumerate(cases4):
        fa, fb = Fraction(a,b), Fraction(c,d)
        res = fa + fb if op == "+" else fa - fb
        correct = frac_text(res)
        level = 5 + i // 2
        naive_n = a + c if op == "+" else a - c
        naive_d = b + d
        ws = [
            wrong(frac_text(Fraction(naive_n, naive_d)) if naive_n else "0", "Du la sammen eller trakk fra både teller og nevner. Finn felles nevner først."),
            wrong(frac_text(Fraction(abs(a-c), max(b,d))) if a != c else f"1/{max(b,d)}", "Brøkene må omskrives til samme nevner før tellerne kan regnes sammen."),
            wrong(frac_text(res + Fraction(1, math.lcm(b,d))), "Du er svært nær, men telleren er én enhet for stor på felles nevner."),
        ]
        common = math.lcm(b,d)
        A = a * (common//b)
        C = c * (common//d)
        steps = [f"Felles nevner for {b} og {d} er {common}.", f"Brøkene blir {A}/{common} og {C}/{common}.", f"{A} {op} {C} = {A+C if op=='+' else A-C}; forkort til {correct}."]
        visual = {"type": "fractionBar", "numerator": res.numerator, "denominator": res.denominator, "label": correct} if i < 4 and res > 0 else None
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="addisjon og subtraksjon med ulik nevner",
                    qtype="standard", prompt=f"Hva er {a}/{b} {op} {c}/{d}?", correct=correct, wrongs=ws,
                    explanation_steps=steps, takeaway=f"Finn felles nevner først. Svaret er {correct}.", visual=visual, tags=["brøkregning"])

    # 10: mixed and improper
    mixed_cases = [(1,2,3), (2,1,4), (3,3,5), (4,2,7), (2,5,6), (5,4,9), (3,7,8), (6,5,11), (4,9,10), (7,3,8)]
    for i, (whole,n,d) in enumerate(mixed_cases):
        improper_n = whole*d+n
        level = 4 + i // 2
        if i % 2 == 0:
            prompt = f"Gjør {whole} {n}/{d} om til uekte brøk."
            correct = f"{improper_n}/{d}"
            ws = [
                wrong(f"{whole+n}/{d}", "Du må gange heltallet med nevneren før telleren legges til."),
                wrong(f"{improper_n}/{whole+d}", "Nevneren skal være den samme."),
                wrong(f"{whole*d}/{d}", "Brøkdelen mangler i telleren."),
            ]
            steps = [f"{whole} hele er {whole*d}/{d}.", f"Legg til {n}/{d}: {whole*d}+{n}={improper_n}.", f"Svaret er {correct}."]
        else:
            prompt = f"Gjør {improper_n}/{d} om til blandet tall."
            correct = f"{whole} {n}/{d}"
            ws = [
                wrong(f"{whole+1} {n}/{d}", "Du har tatt med én hel for mye."),
                wrong(f"{whole} {d-n}/{d}", "Resten etter divisjonen skal være telleren."),
                wrong(f"{n} {whole}/{d}", "Heltall og brøkdel er byttet om."),
            ]
            steps = [f"Del {improper_n} på {d}: det går {whole} hele ganger med rest {n}.", f"Resten blir teller: {whole} {n}/{d}."]
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="blandet tall og uekte brøk",
                    qtype="standard", prompt=prompt, correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"Riktig form er {correct}.", tags=["blandet tall"])

    # 10: word problems
    contexts = [
        (3,5,40,"elever","I en klasse er det 40 elever. 3/5 sykler til skolen. Hvor mange elever sykler til skolen?"),
        (2,3,24,"epler","Det ligger 24 epler i en kurv. 2/3 brukes i en pai. Hvor mange epler brukes?"),
        (5,8,64,"km","En tur er 64 km lang. 5/8 er tilbakelagt. Hvor mange kilometer er tilbakelagt?"),
        (7,10,90,"minutter","En aktivitet varer 90 minutter. 7/10 av tiden brukes til trening. Hvor mange minutter brukes til trening?"),
        (4,9,72,"sider","En bok har 72 sider. 4/9 er lest. Hvor mange sider er lest?"),
        (3,4,56,"kort","I et spill er det 56 kort. 3/4 er røde. Hvor mange røde kort er det?"),
        (5,6,48,"liter","En tank rommer 48 liter. Den er fylt til 5/6. Hvor mange liter er det i tanken?"),
        (7,12,84,"kaker","Et bakeri har 84 kaker. 7/12 blir solgt. Hvor mange kaker blir solgt?"),
        (9,20,200,"kroner","Du har 200 kroner. 9/20 blir spart. Hvor mange kroner blir spart?"),
        (11,15,150,"meter","Et gjerde er 150 meter langt. 11/15 er malt. Hvor mange meter er malt?"),
    ]
    for i, (n,d,total,unit,prompt) in enumerate(contexts):
        ans = total*n//d
        level = 3 + i//2
        correct = with_unit(ans, unit, 0)
        ws = [
            wrong(with_unit(total//d, unit, 0), f"Du fant bare 1/{d}. Gang med {n}."),
            wrong(with_unit(total-ans, unit, 0), "Dette er det som er igjen, ikke delen spørsmålet ber om."),
            wrong(with_unit(total*d//n if total*d%n==0 else total*d, unit, 0), "Teller og nevner er brukt motsatt vei."),
        ]
        steps = [f"Finn 1/{d}: {total} ÷ {d} = {total//d}.", f"Gang med {n}: {total//d} · {n} = {ans}."]
        builder.add(topic="Brøk", grade=grade_level(level), level=level, skill="brøk i tekstoppgaver", qtype="standard",
                    prompt=prompt, correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"{n}/{d} av {total} er {ans} {unit}.", tags=["problemløsing", "brøk"])

    # 5: fraction of remaining, challenges
    cases5 = [(2,5,18), (3,8,25), (4,7,27), (5,12,35), (7,15,48)]
    for i, (start_n, start_d, remaining) in enumerate(cases5):
        left_frac = Fraction(start_d-start_n, start_d)
        total = Fraction(remaining, 1) / left_frac
        if total.denominator != 1:
            # choose a compatible remaining value deterministically
            remaining = left_frac.numerator * (10+i*2)
            total = Fraction(remaining, 1) / left_frac
        total_i = total.numerator
        level = 6 + i
        prompt = f"{start_n}/{start_d} av en mengde er brukt. Det er {remaining} igjen. Hvor stor var mengden først?"
        correct = str(total_i)
        ws = [
            wrong(str(remaining * start_d // start_n if remaining*start_d%start_n==0 else remaining*start_d), "Du behandlet det som er igjen som den brukte brøkdelen."),
            wrong(str(remaining + total_i - remaining - 1), "Du er nær, men har regnet brøkdelen av totalen feil."),
            wrong(str(remaining), "Dette er bare mengden som er igjen, ikke hele mengden."),
        ]
        steps = [f"Det som er igjen er {left_frac.numerator}/{left_frac.denominator} av hele mengden.", f"{left_frac.numerator}/{left_frac.denominator} tilsvarer {remaining}.", f"Hele mengden blir {total_i}."]
        visual = {"type":"fractionBar","numerator":left_frac.numerator,"denominator":left_frac.denominator,"label":"igjen"}
        builder.add(topic="Brøk", grade=7, level=level, skill="finne helheten fra en brøk", qtype="challenge",
                    prompt=prompt, correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"Hele mengden var {total_i}.", visual=visual, tags=["omvendt brøk", "problemløsing"])


def add_desimal(builder: BankBuilder) -> None:
    # 10 place value
    values = ["4,72", "18,305", "0,684", "73,049", "6,507", "120,406", "9,999", "45,081", "0,125", "302,070"]
    places = [("tideler",1),("hundredeler",2),("tusendeler",3)]
    for i, s in enumerate(values):
        dec = s.replace(",", ".")
        frac = dec.split(".")[1]
        name, pos = places[i % 3]
        digit = frac[pos-1] if len(frac) >= pos else "0"
        level = 1 + i//3
        prompt = f"Hvilket siffer står på {name}plassen i tallet {s}?"
        correct = digit
        other_digits = unique([frac[0], frac[-1], str((int(digit)+1)%10), str((int(digit)+5)%10)])
        ws = [wrong(x, f"Se på plassverdien: {name} er siffer nummer {pos} etter komma.") for x in other_digits if x != digit][:3]
        builder.add(topic="Desimaltall", grade=grade_level(level), level=level, skill="plassverdi", qtype="quick",
                    prompt=prompt, correct=correct, wrongs=ws,
                    explanation_steps=[f"Kommaet skiller hele tall fra desimaler.", f"Siffer nummer {pos} etter komma er {digit}."],
                    takeaway=f"På {name}plassen står {digit}.", tags=["plassverdi"])

    # 10 add/subtract decimals
    pairs = [(3.4,2.75),(8.06,1.9),(12.5,7.38),(20.0,6.47),(4.875,2.125),
             (15.6,8.95),(100.0,37.45),(9.08,3.7),(24.35,11.875),(50.5,19.98)]
    for i,(a,b) in enumerate(pairs):
        op = "+" if i%2==0 else "−"
        if op=="−" and a < b: a,b=b,a
        ans = a+b if op=="+" else a-b
        level = 3 + i//3
        correct=nb_num(ans,3)
        wrong_no_align = nb_num((int(a)+int(b)) + (a-int(a)) if op=="+" else abs((int(a)-int(b)) + (a-int(a))),3)
        ws=[
            wrong(wrong_no_align,"Du ser ut til å ha stilt desimalene feil. Komma skal stå under komma."),
            wrong(nb_num(ans+0.1,3),"Sjekk tidelsplassen."),
            wrong(nb_num(abs(a-b) if op=="+" else a+b,3),"Du brukte motsatt regneart."),
        ]
        steps=["Still tallene under hverandre med komma under komma.",f"Regn {nb_num(a,3)} {op} {nb_num(b,3)}.",f"Svaret blir {correct}."]
        builder.add(topic="Desimaltall",grade=grade_level(level),level=level,skill="addisjon og subtraksjon med desimaltall",
                    qtype="standard",prompt=f"Hva er {nb_num(a,3)} {op} {nb_num(b,3)}?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"Komma under komma gir {correct}.",tags=["desimaltall"])

    # 10 multiply/divide by powers of ten
    cases=[(4.7,10,"×"),(0.63,100,"×"),(58.2,10,"÷"),(735,100,"÷"),(0.084,1000,"×"),
           (92.5,100,"÷"),(6.04,100,"×"),(480,1000,"÷"),(0.009,1000,"×"),(125.6,10,"÷")]
    for i,(v,f,op) in enumerate(cases):
        ans=v*f if op=="×" else v/f
        level=2+i//3
        correct=nb_num(ans,4)
        opposite=v/f if op=="×" else v*f
        ws=[
            wrong(nb_num(opposite,4),"Kommaet ble flyttet i motsatt retning."),
            wrong(nb_num(ans*10,4),"Du flyttet kommaet én plass for langt."),
            wrong(nb_num(ans/10,4),"Du flyttet kommaet én plass for lite."),
        ]
        direction="høyre" if op=="×" else "venstre"
        zeros=int(math.log10(f))
        steps=[f"{op} {f} flytter kommaet {zeros} plass{'er' if zeros>1 else ''} mot {direction}.",f"Resultatet er {correct}."]
        builder.add(topic="Desimaltall",grade=grade_level(level),level=level,skill="gange og dele med 10, 100 og 1000",
                    qtype="quick",prompt=f"Hva er {nb_num(v,4)} {op} {f}?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"Flytt kommaet mot {direction}: {correct}.",tags=["plassverdi"])

    # 10 decimal times integer
    cases2=[(2.5,4),(1.75,6),(3.2,15),(0.85,12),(4.25,8),(6.4,25),(2.08,14),(7.5,16),(0.625,32),(12.35,7)]
    for i,(v,n) in enumerate(cases2):
        ans=Decimal(str(v))*n
        level=4+i//2
        correct=nb_num(ans,3)
        ws=[
            wrong(nb_num(Decimal(str(v))+n,3),"Du la sammen i stedet for å multiplisere."),
            wrong(nb_num(ans/10,3),"Kommaet er plassert én plass for langt til venstre."),
            wrong(nb_num(ans+Decimal('1'),3),"Sjekk multiplikasjonen av heltallsdelen og desimaldelen."),
        ]
        steps=[f"Regn først uten komma: {str(v).replace('.','')} · {n}.",f"Plasser kommaet slik at svaret får riktig antall desimaler.",f"Svaret er {correct}."]
        builder.add(topic="Desimaltall",grade=grade_level(level),level=level,skill="multiplikasjon med desimaltall",
                    qtype="standard",prompt=f"Hva er {nb_num(v,3)} · {n}?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"Produktet er {correct}.",tags=["desimaltall","multiplikasjon"])

    # 10 compare/round number line visuals
    vals=[(3.47,3.5),(7.08,7.8),(0.64,0.604),(12.35,12.305),(5.99,6.01),(18.49,18.5),(2.075,2.75),(9.009,9.09),(14.125,14.12),(0.999,1.0)]
    for i,(a,b) in enumerate(vals):
        level=3+i//3
        if i%2==0:
            correct=nb_num(max(a,b),3)
            prompt=f"Hvilket tall er størst: {nb_num(a,3)} eller {nb_num(b,3)}?"
            ws=[
                wrong(nb_num(min(a,b),3),"Sammenlign først heltallsdelen, deretter tideler, hundredeler og tusendeler."),
                wrong(nb_num(abs(a-b),3),"Dette er forskjellen mellom tallene, ikke det største tallet."),
                wrong(nb_num((a+b)/2,3),"Dette er omtrent midt mellom tallene."),
            ]
            steps=["Skriv gjerne like mange desimaler ved å fylle med nuller.",f"Sammenlign plass for plass: {correct} er størst."]
        else:
            ans=Decimal(str(a)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            correct=nb_num(ans,1)
            prompt=f"Rund {nb_num(a,3)} av til nærmeste tidel."
            ws=[
                wrong(nb_num(math.floor(a*10)/10,1),"Du rundet alltid ned. Se på hundredelsplassen."),
                wrong(nb_num(math.ceil(a*10)/10+0.1,1),"Du rundet ett hakk for langt opp."),
                wrong(nb_num(a,3),"Dette er tallet før avrunding."),
            ]
            steps=["Se på hundredelsplassen.",f"Rund tidelsplassen til {correct}."]
        visual={"type":"numberLine","min":math.floor(min(a,b))-1,"max":math.ceil(max(a,b))+1,"points":[a,b]}
        builder.add(topic="Desimaltall",grade=grade_level(level),level=level,skill="sammenligne og avrunde desimaltall",
                    qtype="standard",prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"Riktig svar er {correct}.",visual=visual,tags=["tallinje","desimaltall"])


def add_prosent(builder: BankBuilder) -> None:
    # 10 percent of amount
    cases=[(10,240),(25,80),(30,250),(15,300),(40,175),(12,450),(35,260),(60,140),(75,96),(18,350)]
    for i,(p,total) in enumerate(cases):
        ans=Decimal(p)*Decimal(total)/100
        level=2+i//2
        correct=nb_num(ans,2)
        ws=[
            wrong(nb_num(total-p,2),"Du trakk prosenttallet som om det var et vanlig tall."),
            wrong(nb_num(Decimal(total)/Decimal(p),2),"Du delte på prosenttallet i stedet for å finne prosentdelen."),
            wrong(nb_num(ans*10,2),"Du har brukt tideler i stedet for hundredeler."),
        ]
        steps=[f"Skriv {p} % som {p}/100.",f"{p}/100 · {total} = {correct}."]
        visual={"type":"percentGrid","percent":p} if i<6 else None
        builder.add(topic="Prosent",grade=grade_level(level),level=level,skill="prosent av en mengde",qtype="quick" if level<5 else "standard",
                    prompt=f"Hva er {p} % av {total}?",correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"{p} % av {total} er {correct}.",visual=visual,tags=["prosent"])

    # 10 conversions
    values=[Fraction(1,2),Fraction(1,4),Fraction(3,4),Fraction(1,5),Fraction(2,5),Fraction(3,5),Fraction(1,8),Fraction(3,8),Fraction(7,10),Fraction(9,20)]
    for i,f in enumerate(values):
        percent_value=float(f*100)
        percent_text=nb_num(percent_value,1)
        decimal=nb_num(float(f),3)
        level=2+i//3
        mode=i%3
        if mode==0:
            prompt=f"Hvor mange prosent er {frac_text(f)}?"; correct=f"{percent_text} %"
            ws=[wrong(f"{nb_num(f.numerator*10,1)} %","Du har ikke tatt hensyn til nevneren."),wrong(f"{f.denominator} %","Nevneren er ikke prosentverdien."),wrong(f"{nb_num(100-percent_value,1)} %","Dette er resten opp til 100 %. ")]
        elif mode==1:
            prompt=f"Hvilket desimaltall er det samme som {percent_text} %?"; correct=decimal
            ws=[wrong(percent_text,"Prosent må deles på 100 for å bli desimaltall."),wrong(nb_num(percent_value/10,2),"Du delte bare på 10. Prosent betyr hundredeler."),wrong(nb_num(1-float(f),3),"Dette er delen som mangler opp til 1.")]
        else:
            prompt=f"Hvilken brøk er det samme som {decimal}?"; correct=frac_text(f)
            ws=[wrong(f"{f.numerator}/{f.denominator*10}","Desimaltallet har blitt gjort ti ganger for lite."),wrong(f"{f.denominator}/{f.numerator}","Du har byttet om teller og nevner i brøken."),wrong(frac_text(Fraction(1,1)-f),"Dette er resten opp til én hel.")]
        steps=[
            f"Del telleren på nevneren: {f.numerator} ÷ {f.denominator} = {decimal}.",
            f"Gjør desimaltallet om til prosent ved å gange med 100: {decimal} = {percent_text} %.",
        ]
        visual={"type":"percentGrid","percent":percent_value}
        builder.add(topic="Prosent",grade=grade_level(level),level=level,skill="brøk, desimaltall og prosent",qtype="quick",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"{frac_text(f)}, {decimal} og {percent_text} % er samme verdi.",visual=visual,tags=["representasjoner"])

    # 10 discount
    cases2=[(400,25),(800,30),(1200,15),(350,20),(960,35),(1500,40),(249,10),(1290,25),(750,12),(2200,18)]
    for i,(price,p) in enumerate(cases2):
        discount=Decimal(price)*Decimal(p)/100
        new=Decimal(price)-discount
        level=4+i//2
        correct=money(new)
        ws=[
            wrong(money(discount),"Du fant rabatten riktig, men spørsmålet ber om prisen etter rabatten."),
            wrong(money(Decimal(price)+discount),"Rabatt skal trekkes fra, ikke legges til."),
            wrong(money(Decimal(price)-Decimal(p)),"Prosenttallet er ikke et antall kroner."),
        ]
        steps=[f"Finn rabatten: {p} % av {price} kr = {money(discount)}.",f"Trekk rabatten fra: {price} kr − {money(discount)} = {correct}."]
        visual={"type":"priceTag","price":price,"percent":p}
        builder.add(topic="Prosent",grade=grade_level(level),level=level,skill="rabatt",qtype="standard",
                    prompt=f"En vare koster {price} kr og settes ned med {p} %. Hva er ny pris?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"Ny pris er {correct}.",visual=visual,tags=["rabatt","økonomi"])

    # 10 increase/decrease
    cases3=[(500,10,"øker"),(240,25,"øker"),(900,20,"synker"),(120,15,"øker"),(750,8,"synker"),
            (1600,12,"øker"),(425,30,"synker"),(80,50,"øker"),(2500,6,"synker"),(360,40,"øker")]
    for i,(start,p,direction) in enumerate(cases3):
        change=Decimal(start)*Decimal(p)/100
        ans=Decimal(start)+change if direction=="øker" else Decimal(start)-change
        level=5+i//2
        correct=nb_num(ans,2)
        ws=[
            wrong(nb_num(change,2),"Dette er selve endringen, ikke den nye verdien."),
            wrong(nb_num(Decimal(start)-change if direction=="øker" else Decimal(start)+change,2),"Du brukte motsatt retning på endringen."),
            wrong(nb_num(Decimal(start)+(Decimal(p) if direction=="øker" else -Decimal(p)),2),"Prosenttallet er ikke det samme som et vanlig antall."),
        ]
        op="legg til" if direction=="øker" else "trekk fra"
        steps=[f"Finn endringen: {p} % av {start} = {nb_num(change,2)}.",f"{op.capitalize()} endringen: ny verdi = {correct}."]
        builder.add(topic="Prosent",grade=grade_level(level),level=level,skill="prosentvis økning og nedgang",qtype="standard",
                    prompt=f"En verdi er {start} og {direction} med {p} %. Hva blir den nye verdien?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"Ny verdi er {correct}.",tags=["prosentvis endring"])

    # 10 find whole from percent
    cases4=[(25,45),(20,36),(30,72),(40,84),(15,60),(60,144),(75,180),(12,54),(35,98),(80,216)]
    for i,(p,part) in enumerate(cases4):
        whole=Decimal(part)*100/Decimal(p)
        level=6+i//2
        correct=nb_num(whole,2)
        ws=[
            wrong(nb_num(Decimal(part)*Decimal(p)/100,2),"Du fant prosent av delen, men vi skal finne hele mengden."),
            wrong(nb_num(Decimal(part)+Decimal(p),2),"Prosent og antall kan ikke legges direkte sammen."),
            wrong(nb_num(Decimal(part)*100/Decimal(100-p),2),"Du brukte resten av prosentene i stedet for oppgitt prosentdel."),
        ]
        steps=[f"{p} % tilsvarer {part}.",f"1 % er {part} ÷ {p} = {nb_num(Decimal(part)/p,3)}.",f"100 % er {correct}."]
        visual={"type":"progressBar","percent":p,"label":str(part)} if i<5 else None
        builder.add(topic="Prosent",grade=grade_level(level),level=level,skill="finne helheten fra prosent",qtype="challenge" if level>=9 else "standard",
                    prompt=f"{p} % av et tall er {part}. Hva er hele tallet?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"Hele tallet er {correct}.",visual=visual,tags=["omvendt prosent"])

    # 5 percentage points/part whole
    cases5=[(20,35),(45,60),(12,27),(68,82),(5,25)]
    for i,(before,after) in enumerate(cases5):
        pp=after-before
        relative=(after-before)/before*100
        level=7+i//2
        if i%2==0:
            prompt=f"En andel øker fra {before} % til {after} %. Hvor mange prosentpoeng er økningen?"; correct=f"{pp} prosentpoeng"
            ws=[wrong(f"{nb_num(relative,1)} %","Dette er prosentvis økning, ikke prosentpoeng."),wrong(f"{after} prosentpoeng","Dette er sluttandelen."),wrong(f"{before} prosentpoeng","Dette er startandelen.")]
            steps=[f"Prosentpoeng er forskjellen mellom prosenttallene.",f"{after} − {before} = {pp} prosentpoeng."]
        else:
            prompt=f"I en gruppe på 100 går andelen fra {before} % til {after} %. Hvor mange flere personer er det?"; correct=str(pp)
            ws=[wrong(str(after),"Dette er antallet etter endringen, ikke hvor mange flere."),wrong(str(before),"Dette er antallet før endringen."),wrong(nb_num(relative,1),"Dette er prosentvis vekst, ikke forskjellen i antall av 100.")]
            steps=[f"Av 100 personer betyr {before} % {before} personer og {after} % {after} personer.",f"Forskjellen er {pp}."]
        builder.add(topic="Prosent",grade=7,level=level,skill="prosentpoeng og andeler",qtype="challenge",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Forskjellen er {pp}.",tags=["prosentpoeng"])


def add_algebra(builder: BankBuilder) -> None:
    # 10 one-step equations
    cases=[("+",17,42),("-",12,31),("*",6,54),("/",7,9),("+",38,91),("-",25,64),("*",9,117),("/",12,8),("+",125,300),("*",14,210)]
    for i,(op,k,result) in enumerate(cases):
        if op=="+": x=result-k; prompt=f"x + {k} = {result}"
        elif op=="-": x=result+k; prompt=f"x − {k} = {result}"
        elif op=="*": x=result//k; prompt=f"{k}x = {result}"
        else: x=result*k; prompt=f"x ÷ {k} = {result}"
        level=2+i//3
        correct=str(x)
        ws=[wrong(str(result),"Dette er høyresiden, ikke verdien av x."),wrong(str(abs(x-k)),"Sjekk hvilken motsatt regneart som løser ligningen."),wrong(str(x+k),"Du brukte samme regneart i stedet for den motsatte.")]
        inverse={"+":"trekk fra","-":"legg til","*":"del på","/":"gang med"}[op]
        steps=[f"Isoler x ved å {inverse} {k} på begge sider.",f"Da får vi x = {x}."]
        builder.add(topic="Algebra og mønster",grade=grade_level(level),level=level,skill="ettstegsligninger",qtype="quick",
                    prompt=f"Løs ligningen: {prompt}",correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"x = {x}.",tags=["ligning"])

    # 10 two-step equations
    cases2=[(3,5,26),(4,7,39),(5,-3,42),(6,8,62),(7,-4,45),(8,12,84),(9,-5,76),(4,15,55),(12,-6,90),(11,9,130)]
    for i,(a,b,c) in enumerate(cases2):
        # ensure integer x; adjust c if needed
        x=(c-b)/a
        if x!=int(x):
            x=3+i
            c=a*x+b
        x=int(x)
        sign="+" if b>=0 else "−"
        prompt=f"{a}x {sign} {abs(b)} = {c}"
        level=5+i//2
        correct=str(x)
        after=c-b
        ws=[
            wrong(str((c//a) if c%a==0 else round(c/a,1)),"Du delte før du fjernet konstantleddet."),
            wrong(str(x+1),"Kontroller siste divisjon."),
            wrong(str(after),f"{after} er verdien av {a}x, ikke x."),
        ]
        first_op="trekk fra" if b>=0 else "legg til"
        steps=[f"{first_op.capitalize()} {abs(b)} på begge sider: {a}x = {after}.",f"Del begge sider på {a}: x = {x}."]
        builder.add(topic="Algebra og mønster",grade=grade_level(level),level=level,skill="tostegsligninger",qtype="standard",
                    prompt=f"Løs ligningen: {prompt}",correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"x = {x}.",tags=["ligning"])

    # 10 sequences
    seqs=[([3,7,11,15],4),([2,6,18,54],3),([40,35,30,25],-5),([1,4,9,16],None),([5,10,20,40],2),
          ([100,90,81,73],None),([2,5,10,17],None),([81,27,9,3],Fraction(1,3)),([7,12,17,22],5),([1,2,4,7,11],None)]
    nexts=[19,162,20,25,80,66,26,1,27,16]
    rules=["legg til 4","gang med 3","trekk fra 5","kvadrattall","dobling","trekk fra 10, 9, 8, ...","legg til 3, 5, 7, ...","del på 3","legg til 5","legg til 1, 2, 3, 4, ..."]
    for i,(seq,_) in enumerate(seqs):
        ans=nexts[i]; level=3+i//2
        prompt="Hva er neste tall i følgen: " + ", ".join(map(str,seq)) + ", …?"
        ws=[wrong(str(ans+(i%3+1)),"Forskjellen følger ikke mønsteret hele veien."),wrong(str(seq[-1]+(seq[-1]-seq[-2])),"Du fortsatte bare den siste differansen; se om differansene selv har et mønster."),wrong(str(seq[-1]),"Følgen endrer seg for hvert ledd.")]
        steps=[f"Regelen er: {rules[i]}.",f"Neste tall blir {ans}."]
        visual={"type":"pattern","values":seq}
        builder.add(topic="Algebra og mønster",grade=grade_level(level),level=level,skill="tallmønster",qtype="standard",
                    prompt=prompt,correct=str(ans),wrongs=ws,explanation_steps=steps,takeaway=f"Neste tall er {ans}.",visual=visual,tags=["mønster"])

    # 10 substitute expressions
    cases3=[(2,3,4),(3,5,2),(4,-1,6),(5,7,3),(6,-4,5),(7,2,8),(8,-6,4),(9,10,2),(12,-3,7),(15,5,6)]
    for i,(a,b,x) in enumerate(cases3):
        ans=a*x+b
        level=4+i//2
        sign="+" if b>=0 else "−"
        expr=f"{a}x {sign} {abs(b)}"
        correct=str(ans)
        ws=[wrong(str(a+b+x),"Du la sammen alle tallene. x skal erstattes og multipliseres med koeffisienten."),wrong(str(a*(x+b)),"Du satte hele summen i parentes, men uttrykket har ingen slik parentes."),wrong(str(a*x-b),"Fortegnet på konstantleddet ble brukt feil.")]
        steps=[f"Sett inn x = {x}: {a} · {x} {sign} {abs(b)}.",f"Regn multiplikasjonen først, og få {ans}."]
        builder.add(topic="Algebra og mønster",grade=grade_level(level),level=level,skill="sette inn verdi i uttrykk",qtype="standard",
                    prompt=f"Hva er verdien av {expr} når x = {x}?",correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"Uttrykket får verdien {ans}.",tags=["uttrykk"])

    # 10 inequalities/function tables
    inequality_cases = [
        ("2x + 3 > 11", "x > 4", [
            Wrong("x ≥ 4", "x = 4 gir 11, men ulikheten krever et tall som er større enn 11."),
            Wrong("x < 4", "Løsningen ligger på den andre siden av 4."),
            Wrong("x > 7", "Du trenger ikke legge 3 til grensen etter at ligningen er løst."),
        ], ["Trekk fra 3 på begge sider: 2x > 8.", "Del på 2: x > 4."], 6, 4, "right", False),
        ("3x − 6 ≤ 12", "x ≤ 6", [
            Wrong("x < 6", "x = 6 er også med fordi tegnet er ≤."),
            Wrong("x ≥ 6", "Retningen er motsatt: større x gir større venstreside."),
            Wrong("x ≤ 2", "Du delte før du la til 6."),
        ], ["Legg til 6 på begge sider: 3x ≤ 18.", "Del på 3: x ≤ 6."], 7, 6, "left", True),
        ("x + 5 < 9", "x < 4", [
            Wrong("x ≤ 4", "x = 4 gir 9, men 9 er ikke mindre enn 9."),
            Wrong("x > 4", "Du flyttet grensen til riktig tall, men valgte feil retning."),
            Wrong("x < 14", "Du la sammen i stedet for å trekke fra 5."),
        ], ["Trekk fra 5 på begge sider.", "Da får vi x < 4."], 7, 4, "left", False),
        ("4x + 8 ≥ 24", "x ≥ 4", [
            Wrong("x > 4", "x = 4 gir 24, så 4 skal være med."),
            Wrong("x ≤ 4", "Retningen er motsatt: større x gjør venstresiden større."),
            Wrong("x ≥ 8", "8 skal først trekkes fra 24 før du deler på 4."),
        ], ["Trekk fra 8 på begge sider: 4x ≥ 16.", "Del på 4: x ≥ 4."], 8, 4, "right", True),
        ("18 − 2x > 8", "x < 5", [
            Wrong("x > 5", "Når du deler en ulikhet på et negativt tall, må ulikhetstegnet snus."),
            Wrong("x ≤ 5", "x = 5 gir 8, og 8 er ikke større enn 8."),
            Wrong("x < 13", "Du må isolere leddet −2x før du deler."),
        ], ["Trekk fra 18 på begge sider: −2x > −10.", "Del på −2 og snu ulikhetstegnet: x < 5."], 10, 5, "left", False),
    ]
    function_cases = [(2, 4, 4), (3, 6, 5), (4, 8, 6), (5, 10, 7), (6, 12, 8)]
    for i in range(10):
        if i % 2 == 0:
            expression, correct, wrongs, steps, level, bound, direction, closed = inequality_cases[i // 2]
            prompt = f"Løs ulikheten: {expression}"
            visual = {"type": "numberLine", "min": bound - 6, "max": bound + 6,
                      "boundary": bound, "direction": direction, "closed": closed}
            skill = "ulikheter"
        else:
            a, b, x = function_cases[i // 2]
            level = 6 + i // 2
            y = a * x + b
            prompt = f"En regel er y = {a}x + {b}. Hva er y når x = {x}?"
            correct = str(y)
            wrongs = [
                wrong(str(a + b + x), "Du la sammen i stedet for å gange a med x først."),
                wrong(str(a * (x + b)), "Du satte x + b i parentes, men regelen har ikke den parentesen."),
                wrong(str(y - a), "Sjekk multiplikasjonen av a og x."),
            ]
            steps = [f"Sett inn x = {x}: y = {a} · {x} + {b}.", f"y = {a*x} + {b} = {y}."]
            visual = {"type": "functionTable", "a": a, "b": b, "x": x}
            skill = "funksjonsregel"
        builder.add(
            topic="Algebra og mønster", grade=7, level=level, skill=skill,
            qtype="challenge" if level >= 9 else "standard", prompt=prompt,
            correct=correct, wrongs=wrongs, explanation_steps=steps,
            takeaway=f"Riktig svar er {correct}.", visual=visual, tags=["algebra"],
        )


def add_geometri(builder: BankBuilder) -> None:
    # 10 rectangle perimeter/area
    dims=[(8,5),(12,7),(15,9),(6.5,4),(18,11),(7.5,3.2),(24,13),(9.6,5.5),(32,17),(14.25,8)]
    for i,(w,h) in enumerate(dims):
        area_mode=i%2==0
        level=2+i//2
        if area_mode:
            ans=w*h; prompt=f"Et rektangel er {nb_num(w,2)} cm langt og {nb_num(h,2)} cm bredt. Hva er arealet?"; correct=with_unit(ans,"cm²",2)
            ws=[wrong(with_unit(2*(w+h),"cm²",2),"Du fant omkretsen. Areal er lengde · bredde."),wrong(with_unit(w+h,"cm²",2),"Du la sammen sidene, men areal krever multiplikasjon."),wrong(with_unit(ans*2,"cm²",2),"Du har doblet arealet uten grunn.")]
            steps=["Areal av et rektangel er lengde · bredde.",f"{nb_num(w,2)} · {nb_num(h,2)} = {nb_num(ans,2)} cm²."]
            skill="areal av rektangel"
        else:
            ans=2*(w+h); prompt=f"Et rektangel er {nb_num(w,2)} cm langt og {nb_num(h,2)} cm bredt. Hva er omkretsen?"; correct=with_unit(ans,"cm",2)
            ws=[wrong(with_unit(w*h,"cm",2),"Du fant arealet. Omkrets er summen rundt kanten."),wrong(with_unit(w+h,"cm",2),"Du tok bare én lengde og én bredde. Begge forekommer to ganger."),wrong(with_unit(ans+h,"cm",2),"En side er telt én gang for mye.")]
            steps=["Omkretsen er summen av alle fire sidene.",f"2 · ({nb_num(w,2)} + {nb_num(h,2)}) = {nb_num(ans,2)} cm."]
            skill="omkrets av rektangel"
        visual={"type":"rectangle","width":w,"height":h,"unit":"cm"}
        builder.add(topic="Geometri",grade=grade_level(level),level=level,skill=skill,qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Svaret er {correct}.",visual=visual,tags=["rektangel"])

    # 8 triangle area
    dims2=[(10,6),(14,9),(8,7),(12.5,4),(18,11),(9.6,5),(25,12),(16.5,8)]
    for i,(base,height) in enumerate(dims2):
        area=base*height/2; level=4+i//2; correct=with_unit(area,"cm²",2)
        ws=[wrong(with_unit(base*height,"cm²",2),"Du glemte å dele på 2. En trekant er halvparten av et rektangel med samme grunnlinje og høyde."),wrong(with_unit((base+height)/2,"cm²",2),"Arealformelen bruker produktet av grunnlinje og høyde."),wrong(with_unit(base+height,"cm²",2),"Du la sammen lengdene. Areal måles i kvadratenheter.")]
        steps=["Areal av trekant = grunnlinje · høyde ÷ 2.",f"{nb_num(base,2)} · {nb_num(height,2)} ÷ 2 = {nb_num(area,2)} cm²."]
        visual={"type":"triangle","base":base,"height":height,"unit":"cm"}
        builder.add(topic="Geometri",grade=grade_level(level),level=level,skill="areal av trekant",qtype="standard",
                    prompt=f"En trekant har grunnlinje {nb_num(base,2)} cm og høyde {nb_num(height,2)} cm. Hva er arealet?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Arealet er {correct}.",visual=visual,tags=["trekant","areal"])

    # 7 circles
    circles=[(5,"radius"),(10,"diameter"),(7,"radius"),(14,"diameter"),(4.5,"radius"),(18,"diameter"),(12,"radius")]
    pi = Decimal("3.14")
    for i,(v,kind) in enumerate(circles):
        radius=Decimal(str(v if kind=="radius" else v/2))
        diameter=radius*2
        mode=i%3
        level=5+i//2
        if mode==0:
            ans=diameter; prompt=f"En sirkel har radius {nb_num(radius,1)} cm. Hva er diameteren?"; correct=with_unit(ans,"cm",1)
            ws=[wrong(with_unit(radius,"cm",1),"Dette er radiusen, ikke diameteren."),wrong(with_unit(radius*pi,"cm",1),"Dette er omtrent halv omkrets, ikke diameter."),wrong(with_unit(radius+2,"cm",1),"Diameteren er to ganger radiusen.")]
            steps=["Diameter = 2 · radius.",f"2 · {nb_num(radius,1)} = {nb_num(ans,1)} cm."]
            skill="radius og diameter"
            visual_show="radius"
        elif mode==1:
            ans=pi*diameter; prompt=f"En sirkel har diameter {nb_num(diameter,1)} cm. Omtrent hvor stor er omkretsen? Bruk π ≈ 3,14."; correct=with_unit(ans,"cm",1)
            ws=[wrong(with_unit(diameter*2,"cm",1),"Omkretsen er ikke bare dobbelt diameteren; bruk π · diameter."),wrong(with_unit(pi*radius,"cm",1),"Du brukte radius i stedet for diameter."),wrong(with_unit(pi*diameter*2,"cm",1),"Du har doblet omkretsen.")]
            steps=["Omkrets = π · diameter.",f"3,14 · {nb_num(diameter,1)} ≈ {nb_num(ans,1)} cm."]
            skill="sirkelens omkrets"
            visual_show="diameter"
        else:
            ans=pi*radius*radius; prompt=f"En sirkel har radius {nb_num(radius,1)} cm. Omtrent hvor stort er arealet? Bruk π ≈ 3,14."; correct=with_unit(ans,"cm²",1)
            ws=[wrong(with_unit(pi*diameter,"cm²",1),"Dette ligner omkretsformelen. Areal er π · r²."),wrong(with_unit(pi*radius,"cm²",1),"Radiusen må kvadreres."),wrong(with_unit(radius*radius,"cm²",1),"Du mangler faktoren π.")]
            steps=["Areal = π · r².",f"3,14 · {nb_num(radius,1)}² ≈ {nb_num(ans,1)} cm²."]
            skill="sirkelens areal"
            visual_show="radius"
        visual={"type":"circle","radius":float(radius),"show":visual_show}
        builder.add(topic="Geometri",grade=grade_level(level),level=level,skill=skill,qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Svaret er omtrent {correct}.",visual=visual,tags=["sirkel"])

    # 8 angles
    angle_cases=[(35,55),(42,68),(110,25),(75,45),(30,80),(95,40),(125,15),(60,60)]
    for i,(a,b) in enumerate(angle_cases):
        triangle=i%2==0
        if triangle:
            ans=180-a-b; prompt=f"To vinkler i en trekant er {a}° og {b}°. Hvor stor er den tredje vinkelen?"; total=180
            takeaway="Vinklene i en trekant er til sammen 180°."
        else:
            ans=180-a; prompt=f"To nabovinkler ligger på en rett linje. Den ene er {a}°. Hvor stor er den andre?"; total=180
            takeaway="Vinkler på en rett linje er til sammen 180°."
        level=4+i//2; correct=f"{ans}°"
        ws=[wrong(f"{a+b}°","Du fant summen av de kjente vinklene, ikke vinkelen som mangler."),wrong(f"{360-a-b if triangle else 360-a}°","Du brukte 360°, men her er totalsummen 180°."),wrong(f"{abs(a-b)}°","Forskjellen mellom de kjente vinklene gir ikke den ukjente.")]
        steps=[takeaway,f"{total}° − {a}°"+(f" − {b}°" if triangle else "")+f" = {ans}°."]
        visual={"type":"angles","angles":[a,b],"triangle":triangle}
        builder.add(topic="Geometri",grade=grade_level(level),level=level,skill="vinkler",qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Den ukjente vinkelen er {ans}°.",visual=visual,tags=["vinkler"])

    # 6 coordinates/symmetry
    points=[(2,3),(-3,4),(5,-2),(-4,-1),(1,6),(7,1)]
    for i,(x,y) in enumerate(points):
        level=5+i
        if i%2==0:
            prompt=f"Punktet P ligger i ({x}, {y}). Hva blir koordinatene etter speiling i y-aksen?"; correct=f"({-x}, {y})"
            ws=[wrong(f"({x}, {-y})","Dette er speiling i x-aksen."),wrong(f"({-x}, {-y})","Du endret fortegnet på begge koordinater."),wrong(f"({y}, {x})","Du byttet plass på koordinatene.")]
            steps=["Ved speiling i y-aksen skifter x-koordinaten fortegn.",f"({x}, {y}) blir ({-x}, {y})."]
        else:
            prompt=f"Punktet Q ligger i ({x}, {y}). Hva blir koordinatene etter speiling i x-aksen?"; correct=f"({x}, {-y})"
            ws=[wrong(f"({-x}, {y})","Dette er speiling i y-aksen."),wrong(f"({-x}, {-y})","Du endret begge koordinater."),wrong(f"({y}, {x})","Du byttet plass på x og y.")]
            steps=["Ved speiling i x-aksen skifter y-koordinaten fortegn.",f"({x}, {y}) blir ({x}, {-y})."]
        visual={"type":"coordinateGrid","point":[x,y]}
        builder.add(topic="Geometri",grade=grade_level(level),level=level,skill="koordinater og speiling",qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Riktig koordinat er {correct}.",visual=visual,tags=["koordinatsystem"])

    # 6 composite shapes
    cases3=[(10,6,4,2),(12,8,5,3),(15,9,6,4),(20,12,8,5),(18,14,7,6),(25,16,10,7)]
    for i,(W,H,w,h) in enumerate(cases3):
        ans=W*H-w*h; level=min(10,6+i); correct=with_unit(ans,"cm²",0)
        ws=[wrong(with_unit(W*H,"cm²",0),"Du fant arealet av hele det store rektangelet, men utsnittet må trekkes fra."),wrong(with_unit(w*h,"cm²",0),"Dette er bare arealet av utsnittet."),wrong(with_unit(W*H+w*h,"cm²",0),"Utsnittet skal trekkes fra, ikke legges til.")]
        steps=[f"Stort rektangel: {W} · {H} = {W*H} cm².",f"Utsnitt: {w} · {h} = {w*h} cm².",f"{W*H} − {w*h} = {ans} cm²."]
        visual={"type":"compositeL","outer":[W,H],"cutout":[w,h],"unit":"cm"}
        builder.add(topic="Geometri",grade=7,level=level,skill="sammensatte figurer",qtype="challenge",
                    prompt=f"En L-form består av et rektangel {W} cm × {H} cm med et utsnitt {w} cm × {h} cm. Hva er arealet?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Arealet er {correct}.",visual=visual,tags=["sammensatt figur","areal"])


def add_maling(builder: BankBuilder) -> None:
    # 10 unit conversions
    cases=[(3.5,"km","m",3500),(4200,"m","km",4.2),(2.75,"kg","g",2750),(850,"g","kg",0.85),(4.5,"L","mL",4500),
           (3250,"mL","L",3.25),(1.8,"m","cm",180),(560,"cm","m",5.6),(0.75,"tonn","kg",750),(12500,"mg","g",12.5)]
    for i,(v,u1,u2,ans) in enumerate(cases):
        level=2+i//2; correct=with_unit(ans,u2,3)
        ws=[wrong(with_unit(ans*10,u2,3),"Du brukte én null for mye."),wrong(with_unit(ans/10,u2,3),"Du brukte én null for lite."),wrong(with_unit(v,u2,3),"Du beholdt tallet uten å endre for den nye enheten.")]
        steps=[f"Finn forholdet mellom {u1} og {u2}.",f"{nb_num(v,3)} {u1} = {correct}."]
        visual={"type":"ruler","value":v,"from":u1,"to":u2} if i<6 else None
        builder.add(topic="Måling",grade=grade_level(level),level=level,skill="omgjøring av måleenheter",qtype="quick",
                    prompt=f"Gjør om {nb_num(v,3)} {u1} til {u2}.",correct=correct,wrongs=ws,explanation_steps=steps,
                    takeaway=f"Svaret er {correct}.",visual=visual,tags=["måleenheter"])

    # 8 time duration
    times=[((8,35),(10,5)),((13,50),(15,20)),((9,45),(12,10)),((17,25),(19,0)),((6,55),(8,40)),((14,15),(18,5)),((22,30),(1,15)),((11,48),(16,32))]
    for i,(start,end) in enumerate(times):
        s=start[0]*60+start[1]; e=end[0]*60+end[1]
        if e<s: e+=24*60
        mins=e-s; h=mins//60; m=mins%60
        correct=(f"{h} t {m} min" if h and m else f"{h} timer" if h else f"{m} min")
        level=2+i//2
        ws=[wrong(f"{abs(end[0]-start[0])} t {abs(end[1]-start[1])} min","Timer og minutter kan ikke alltid trekkes fra hver for seg uten å låne."),wrong(f"{mins+60} min","Du la til én time for mye."),wrong(f"{max(0,mins-30)} min","Kontroller overgangen over hel time.")]
        steps=[f"Gjør tidspunktene om til minutter eller tell framover fra {start[0]:02d}:{start[1]:02d}.",f"Tidsforskjellen er {mins} minutter, altså {correct}."]
        visual={"type":"clockPair","start":list(start),"end":list(end)}
        builder.add(topic="Måling",grade=grade_level(level),level=level,skill="tid og varighet",qtype="standard",
                    prompt=f"Hvor lang tid går det fra kl. {start[0]:02d}:{start[1]:02d} til kl. {end[0]:02d}:{end[1]:02d}?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Det går {correct}.",visual=visual,tags=["tid"])

    # 7 rectangular prism volume
    dims=[(4,3,5),(6,2,8),(7,5,4),(10,6,3),(12,8,5),(2.5,4,6),(9,7,5.5)]
    for i,(l,w,h) in enumerate(dims):
        v=l*w*h; level=5+i//2; correct=with_unit(v,"cm³",2)
        ws=[wrong(with_unit(l*w,"cm³",2),"Dette er bare grunnflaten. Volum krever også høyden."),wrong(with_unit(2*(l*w+l*h+w*h),"cm³",2),"Dette er overflateareal, ikke volum."),wrong(with_unit(l+w+h,"cm³",2),"Lengdene må multipliseres, ikke legges sammen.")]
        steps=["Volum av et rett prisme = lengde · bredde · høyde.",f"{nb_num(l,2)} · {nb_num(w,2)} · {nb_num(h,2)} = {nb_num(v,2)} cm³."]
        visual={"type":"prism","length":l,"width":w,"height":h,"unit":"cm"}
        builder.add(topic="Måling",grade=grade_level(level),level=level,skill="volum",qtype="standard",
                    prompt=f"En boks er {nb_num(l,2)} cm × {nb_num(w,2)} cm × {nb_num(h,2)} cm. Hva er volumet?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Volumet er {correct}.",visual=visual,tags=["volum"])

    # 5 scale/map
    cases2=[(1,10000,4.5),(1,25000,8),(1,50000,3.2),(1,100000,6.5),(1,200000,7.5)]
    for i,(_,scale,cm) in enumerate(cases2):
        real_cm=cm*scale; km=real_cm/100000
        level=6+i; correct=with_unit(km,"km",2)
        ws=[wrong(with_unit(cm*scale/1000,"km",2),"Du gjorde om centimeter til kilometer med feil faktor."),wrong(with_unit(cm,"km",2),"Kartlengden er ikke den virkelige lengden."),wrong(with_unit(km*10,"km",2),"Du har én null for mye i omregningen.")]
        steps=[f"Målestokk 1:{scale} betyr at 1 cm på kartet er {scale} cm i virkeligheten.",f"{nb_num(cm,1)} · {scale} = {nb_num(real_cm,0)} cm.",f"Det er {nb_num(km,2)} km."]
        visual={"type":"mapScale","scale":scale,"cm":cm}
        builder.add(topic="Måling",grade=grade_level(level),level=level,skill="målestokk",qtype="challenge",
                    prompt=f"På et kart med målestokk 1:{scale} er avstanden {nb_num(cm,1)} cm. Hvor langt er det i virkeligheten?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Virkelig avstand er {correct}.",visual=visual,tags=["målestokk"])

    # 5 rate/speed
    cases3=[(120,3),(150,2.5),(84,1.5),(210,3.5),(96,1.2)]
    for i,(dist,time) in enumerate(cases3):
        speed=dist/time; level=6+i; correct=with_unit(speed,"km/t",1)
        ws=[wrong(with_unit(dist*time,"km/t",1),"Fart er avstand delt på tid, ikke ganget."),wrong(with_unit(time/dist,"km/t",2),"Du delte i motsatt rekkefølge."),wrong(with_unit(dist-time,"km/t",1),"Avstand og tid kan ikke trekkes direkte fra for å finne fart.")]
        steps=["Gjennomsnittsfart = avstand ÷ tid.",f"{dist} km ÷ {nb_num(time,1)} t = {nb_num(speed,1)} km/t."]
        builder.add(topic="Måling",grade=grade_level(level),level=level,skill="fart",qtype="challenge",
                    prompt=f"En tur er {dist} km og tar {nb_num(time,1)} timer. Hva er gjennomsnittsfarten?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Gjennomsnittsfarten er {correct}.",tags=["fart","forhold"])


def add_statistikk(builder: BankBuilder) -> None:
    # 10 statistics measures
    datasets=[[4,6,8,10,12],[3,5,5,7,10],[12,14,15,15,16,18],[2,4,7,9,13],[20,22,22,24,28,34],
              [5,8,8,8,11,14],[6,9,12,15,18],[1,3,3,4,7,9],[10,12,14,18,21],[25,25,27,30,33,35]]
    modes=["mean","mode","median","range","mean","mode","median","range","mean","median"]
    names={"mean":"gjennomsnittet","mode":"typetallet","median":"medianen","range":"variasjonsbredden"}
    for i,(data,mode) in enumerate(zip(datasets,modes)):
        sorted_d=sorted(data)
        mean=sum(data)/len(data)
        median=(sorted_d[len(data)//2] if len(data)%2 else (sorted_d[len(data)//2-1]+sorted_d[len(data)//2])/2)
        counts=Counter(data); modeval=max(counts,key=counts.get)
        rangev=max(data)-min(data)
        ans={"mean":mean,"mode":modeval,"median":median,"range":rangev}[mode]
        correct=nb_num(ans,2); level=4+i//2
        vals=unique([nb_num(mean,2),nb_num(median,2),nb_num(modeval,2),nb_num(rangev,2),nb_num(sum(data),2)])
        ws=[wrong(v,f"Dette er et annet statistisk mål. Oppgaven spør etter {names[mode]}.") for v in vals if v!=correct][:3]
        while len(ws)<3: ws.append(wrong(nb_num(float(ans)+len(ws)+1,2),"Regn statistikkmålet på nytt."))
        if mode=="mean": steps=[f"Legg sammen tallene: summen er {sum(data)}.",f"Del på {len(data)}: {sum(data)} ÷ {len(data)} = {correct}."]
        elif mode=="median": steps=["Sorter tallene.",f"Tallet/tallene i midten gir medianen {correct}."]
        elif mode=="mode": steps=["Tell hvor mange ganger hvert tall forekommer.",f"{correct} forekommer flest ganger."]
        else: steps=[f"Største verdi er {max(data)}, minste er {min(data)}.",f"{max(data)} − {min(data)} = {correct}."]
        visual={"type":"dataDots","values":data}
        builder.add(topic="Statistikk og sannsynlighet",grade=grade_level(level),level=level,skill=names[mode],qtype="standard",
                    prompt=f"Tallene er {', '.join(map(str,data))}. Hva er {names[mode]}?",correct=correct,wrongs=ws,
                    explanation_steps=steps,takeaway=f"{names[mode].capitalize()} er {correct}.",visual=visual,tags=["statistikk"])

    # 10 bar chart
    labels=["Man","Tir","Ons","Tor"]
    chart_sets=[[4,7,5,9],[12,8,15,10],[3,6,11,8],[20,17,14,22],[5,5,8,12],[9,13,7,16],[18,12,19,15],[6,10,14,18],[25,20,30,15],[7,9,12,11]]
    for i,vals in enumerate(chart_sets):
        level=3+i//2
        if i%2==0:
            idx=max(range(4),key=lambda j:vals[j]); correct=labels[idx]
            prompt="Hvilken dag viser søylediagrammet størst verdi?"
            ws=[wrong(l,"Sammenlign høyden på søylene.") for l in labels if l!=correct]
            steps=[f"Den høyeste søylen har verdien {max(vals)}.",f"Den tilhører {correct}."]
        else:
            diff=max(vals)-min(vals); correct=str(diff)
            prompt="Hva er forskjellen mellom største og minste verdi i søylediagrammet?"
            ws=[wrong(str(max(vals)),"Dette er største verdi, ikke forskjellen."),wrong(str(min(vals)),"Dette er minste verdi."),wrong(str(max(vals)+min(vals)),"Du la sammen i stedet for å trekke fra.")]
            steps=[f"Største verdi er {max(vals)}, minste er {min(vals)}.",f"{max(vals)} − {min(vals)} = {diff}."]
        visual={"type":"barChart","labels":labels,"values":vals}
        builder.add(topic="Statistikk og sannsynlighet",grade=grade_level(level),level=level,skill="lese diagram",qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Riktig svar er {correct}.",visual=visual,tags=["diagram"])

    # 10 simple probability
    bags=[(3,7),(5,5),(2,8),(6,4),(1,9),(7,3),(4,6),(8,2),(3,12),(9,6)]
    for i,(red,blue) in enumerate(bags):
        total=red+blue; f=Fraction(red,total); correct=frac_text(f); level=2+i//2
        ws=[
            wrong(frac_text(Fraction(red,blue)),"Nevneren skal være totalt antall kuler, ikke bare de blå."),
            wrong(frac_text(Fraction(blue,total)),"Dette er sannsynligheten for blå kule."),
            wrong(frac_text(Fraction(1,total)),"Dette gjelder bare én bestemt kule, ikke alle røde."),
            wrong(frac_text(Fraction(red,total+1)),"Du har telt én kule for mye i totalen."),
            wrong(frac_text(Fraction(red,total-1)),"Du har glemt én kule i totalen."),
        ]
        raw = f"{red}/{total}"
        probability_step = f"{red} av dem er røde, så sannsynligheten er {raw}." if raw == correct else f"{red} av dem er røde, så sannsynligheten er {raw} = {correct}."
        steps=[f"Det er {total} kuler totalt.", probability_step]
        visual={"type":"probabilityBag","red":red,"blue":blue}
        red_text = "1 rød" if red == 1 else f"{red} røde"
        blue_text = "1 blå" if blue == 1 else f"{blue} blå"
        builder.add(topic="Statistikk og sannsynlighet",grade=grade_level(level),level=level,skill="enkel sannsynlighet",qtype="quick",
                    prompt=f"En pose har {red_text} og {blue_text} kuler. Hva er sannsynligheten for rød kule?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Sannsynligheten er {correct}.",visual=visual,tags=["sannsynlighet"])

    # 5 compound/experimental
    for i in range(5):
        level=min(10,7+i)
        if i<3:
            target=7+i; combos=6-abs(7-target) if target<=7 else 6-abs(target-7)
            combos=max(1,combos); f=Fraction(combos,36); correct=frac_text(f)
            prompt=f"To vanlige terninger kastes. Hva er sannsynligheten for at summen blir {target}?"
            ws=[wrong(f"1/6","Det finnes flere mulige par, og totalt er det 36 kombinasjoner."),wrong(f"{combos}/12","Totalt antall ordnede kombinasjoner er 36, ikke 12."),wrong(frac_text(Fraction(1,36)),"Dette gjelder bare én bestemt kombinasjon.")]
            steps=["To terninger gir 6 · 6 = 36 like sannsynlige ordnede kombinasjoner.",f"Det er {combos} kombinasjoner som gir summen {target}.",f"Sannsynligheten er {combos}/36 = {correct}."]
            visual={"type":"dice","count":2,"target":target}
        else:
            successes=12+i*3; trials=50; f=Fraction(successes,trials); correct=f"{nb_num(successes/trials*100,1)} %"
            prompt=f"I et forsøk skjedde hendelsen {successes} av {trials} ganger. Hva er den eksperimentelle sannsynligheten i prosent?"
            ws=[wrong(f"{successes} %","Antallet treff må deles på totalt antall forsøk."),wrong(f"{nb_num((trials-successes)/trials*100,1)} %","Dette er sannsynligheten for at hendelsen ikke skjer."),wrong(f"{nb_num(successes/trials*10,1)} %","Du ganget med 10 i stedet for 100.")]
            steps=[f"Del treff på forsøk: {successes}/{trials} = {nb_num(successes/trials,2)}.",f"Gang med 100: {correct}."]
            visual={"type":"progressBar","percent":successes/trials*100,"label":f"{successes} av {trials}"}
        builder.add(topic="Statistikk og sannsynlighet",grade=7,level=level,skill="sammensatt og eksperimentell sannsynlighet",qtype="challenge",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Sannsynligheten er {correct}.",visual=visual,tags=["sannsynlighet"])


def add_okonomi(builder: BankBuilder) -> None:
    # 10 totals/change/unit price
    cases=[(3,29.9,100),(4,18.5,100),(2,74.5,200),(5,12.8,100),(6,24.9,200),(3,159,500),(8,9.75,100),(4,87.5,500),(7,34.9,300),(5,249,1500)]
    for i,(qty,price,paid) in enumerate(cases):
        total=Decimal(str(price))*qty; change=Decimal(paid)-total; level=2+i//2
        if i%2==0:
            prompt=f"Du kjøper {qty} varer til {money(price)} per stykk. Hva koster det totalt?"; correct=money(total)
            ws=[wrong(money(Decimal(str(price))+qty),"Du la sammen antall og pris. Pris per stykk må ganges med antallet."),wrong(money(total/qty),"Dette er prisen per stykk."),wrong(money(total+Decimal(str(price))),"Du la til én vare for mye.")]
            steps=[f"Totalpris = {qty} · {money(price)}.",f"Det blir {money(total)}."]
            skill="totalpris"
        else:
            prompt=f"Du kjøper {qty} varer til {money(price)} per stykk og betaler med {paid} kr. Hvor mye får du tilbake?"; correct=money(change)
            ws=[wrong(money(total),"Dette er det varene koster, ikke vekslepengene."),wrong(money(Decimal(paid)+total),"Vekslepenger er betalt beløp minus pris."),wrong(money(change+Decimal('10')),"Sjekk subtraksjonen mellom betalt beløp og totalpris.")]
            steps=[f"Varene koster {qty} · {money(price)} = {money(total)}.",f"Vekslepenger: {paid} kr − {money(total)} = {money(change)}."]
            skill="vekslepenger"
        visual={"type":"receipt","quantity":qty,"unitPrice":price,"paid":paid}
        builder.add(topic="Økonomi",grade=grade_level(level),level=level,skill=skill,qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Svaret er {correct}.",visual=visual,tags=["penger"])

    # 10 budget
    budgets=[(1200,[350,220,180,125]),(950,[199,249,175]),(2000,[450,375,290,310]),(1500,[299,189,255,340]),(800,[125,75,210,90]),
             (2500,[699,450,350,275]),(1100,[249,199,149,99]),(1750,[425,380,215,160]),(3000,[850,720,640,390]),(1400,[325,275,190,155])]
    for i,(income,expenses) in enumerate(budgets):
        total=sum(expenses); left=income-total; level=3+i//2; correct=money(left)
        ws=[wrong(money(total),"Dette er summen av utgiftene, ikke det som er igjen."),wrong(money(income+total),"Utgifter skal trekkes fra inntekten."),wrong(money(left+expenses[-1]),"En av utgiftene ser ut til å mangle.")]
        steps=["Legg sammen alle utgiftene: " + " + ".join(map(str,expenses)) + f" = {total} kr.",f"Trekk fra budsjettet: {income} − {total} = {left} kr."]
        visual={"type":"budget","income":income,"expenses":expenses}
        builder.add(topic="Økonomi",grade=grade_level(level),level=level,skill="budsjett",qtype="standard",
                    prompt=f"Du har et budsjett på {income} kr og utgifter på {', '.join(str(x)+' kr' for x in expenses)}. Hvor mye er igjen?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Det er {correct} igjen.",visual=visual,tags=["budsjett"])

    # 5 simple interest/discount comparisons
    cases2=[(1000,4,2),(2500,3,1),(800,5,3),(1500,2,4),(3200,6,1)]
    for i,(principal,rate,years) in enumerate(cases2):
        interest=Decimal(principal)*Decimal(rate)/100*years; total=Decimal(principal)+interest; level=6+i
        prompt=f"{principal} kr står på en konto med enkel rente {rate} % per år i {years} år. Hvor mye er på kontoen etterpå?"
        correct=money(total)
        ws=[wrong(money(interest),"Dette er rentebeløpet, ikke saldoen etterpå."),wrong(money(Decimal(principal)*(1+Decimal(rate)/100)**years),"Dette er omtrent rentes rente. Oppgaven sier enkel rente."),wrong(money(Decimal(principal)+Decimal(rate)*years),"Renten er prosent av beløpet, ikke bare et antall kroner.")]
        steps=[f"Rente per år: {rate} % av {principal} kr = {money(Decimal(principal)*Decimal(rate)/100)}.",f"For {years} år: {money(interest)}.",f"Saldo: {principal} kr + {money(interest)} = {money(total)}."]
        builder.add(topic="Økonomi",grade=grade_level(level),level=level,skill="enkel rente",qtype="challenge",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Saldoen blir {correct}.",tags=["rente"])

    # 5 compare offers
    offers=[((3,120),(5,185)),((4,199),(6,285)),((2,75),(5,170)),((8,440),(3,174)),((10,599),(4,252))]
    for i,(A,B) in enumerate(offers):
        unitA=A[1]/A[0]; unitB=B[1]/B[0]
        cheaper="Tilbud A" if unitA<unitB else "Tilbud B"
        level=5+i
        correct=cheaper
        ws=[wrong("Tilbud B" if cheaper=="Tilbud A" else "Tilbud A","Sammenlign pris per vare, ikke bare totalprisen."),wrong("De koster like mye per vare","Pris per vare er forskjellig."),wrong("Det kan ikke avgjøres","Vi kan dele totalpris på antall i begge tilbud.")]
        steps=[f"Tilbud A: {A[1]} ÷ {A[0]} = {money(unitA)} per vare.",f"Tilbud B: {B[1]} ÷ {B[0]} = {money(unitB)} per vare.",f"{cheaper} er billigst per vare."]
        visual={"type":"offers","a":{"qty":A[0],"price":A[1]},"b":{"qty":B[0],"price":B[1]}}
        builder.add(topic="Økonomi",grade=grade_level(level),level=level,skill="sammenligne tilbud",qtype="challenge",
                    prompt=f"Tilbud A: {A[0]} varer for {A[1]} kr. Tilbud B: {B[0]} varer for {B[1]} kr. Hvilket er billigst per vare?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"{cheaper} har lavest stykkpris.",visual=visual,tags=["stykkpris"])


def add_problemlosing(builder: BankBuilder) -> None:
    # 10 multistep arithmetic contexts
    contexts=[
        ("kino", 4, 145, 3, 95),
        ("fotballcup", 6, 85, 8, 55),
        ("museum", 3, 120, 5, 70),
        ("båttur", 5, 195, 4, 115),
        ("show", 4, 260, 6, 160),
        ("fotballkamp", 7, 175, 5, 110),
        ("festival", 6, 310, 4, 190),
        ("klatrepark", 5, 235, 7, 165),
        ("vitensenter", 4, 190, 8, 110),
        ("fornøyelsespark", 8, 425, 6, 295),
    ]
    for i,(place,adults,adult_price,children,child_price) in enumerate(contexts):
        total=adults*adult_price+children*child_price; level=3+i//2; correct=money(total)
        prompt=f"En gruppe skal på {place}. De kjøper {adults} voksenbilletter til {adult_price} kr og {children} barnebilletter til {child_price} kr. Hva koster alle billettene til sammen?"
        ws=[wrong(money((adults+children)*(adult_price+child_price)),"Du ganget summen av antall med summen av priser. Regn billettypene hver for seg."),wrong(money(adults*adult_price),"Barnebillettene mangler."),wrong(money(children*child_price),"Voksenbillettene mangler.")]
        steps=[f"Voksenbilletter: {adults} · {adult_price} = {adults*adult_price} kr.",f"Barnebilletter: {children} · {child_price} = {children*child_price} kr.",f"Totalt: {adults*adult_price} + {children*child_price} = {total} kr."]
        builder.add(topic="Problemløsing",grade=grade_level(level),level=level,skill="flerstegsregning",qtype="standard",
                    prompt=prompt,correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Totalprisen er {correct}.",tags=["tekstoppgave","flere steg"])

    # 10 ratios/recipes
    recipes=[(4,6,300,"g mel"),(3,8,450,"mL melk"),(5,12,250,"g ris"),(2,7,180,"g pasta"),(6,15,500,"g kjøtt"),
             (4,10,2,"L saft"),(8,14,640,"g frukt"),(3,9,225,"g ost"),(5,18,750,"mL suppe"),(6,20,480,"g deig")]
    for i,(servings,new_servings,amount,unit) in enumerate(recipes):
        ans=amount*new_servings/servings; level=4+i//2; correct=with_unit(ans,unit,2)
        ws=[wrong(with_unit(amount+new_servings-servings,unit,2),"Mengden må skaleres med et forhold, ikke bare justeres med forskjellen i porsjoner."),wrong(with_unit(amount*servings/new_servings,unit,2),"Forholdet er snudd."),wrong(with_unit(amount*new_servings,unit,2),"Du glemte å dele på opprinnelig antall porsjoner.")]
        steps=[f"Mengde per porsjon: {amount} ÷ {servings} = {nb_num(amount/servings,2)} {unit}.",f"For {new_servings} porsjoner: {nb_num(amount/servings,2)} · {new_servings} = {nb_num(ans,2)} {unit}."]
        visual={"type":"recipe","oldServings":servings,"newServings":new_servings,"amount":amount,"unit":unit}
        builder.add(topic="Problemløsing",grade=grade_level(level),level=level,skill="forhold og oppskrifter",qtype="standard",
                    prompt=f"En oppskrift for {servings} porsjoner bruker {amount} {unit}. Hvor mye trengs til {new_servings} porsjoner?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Du trenger {correct}.",visual=visual,tags=["forhold","oppskrift"])

    # 8 distance/time
    # Each half-distance gives a whole number of minutes at both speeds.
    trips=[(12,4,6),(24,8,6),(30,10,6),(36,12,9),(42,7,14),(48,8,12),(60,15,10),(72,12,18)]
    for i,(total,first_speed,second_speed) in enumerate(trips):
        half=total/2
        first_minutes=int(half/first_speed*60)
        second_minutes=int(half/second_speed*60)
        minutes=first_minutes+second_minutes
        level=5+i//2; correct=f"{minutes} min"
        average_guess=round(total/((first_speed+second_speed)/2)*60)
        ws=[wrong(f"{average_guess} min","Gjennomsnittet av fartene kan ikke brukes direkte når like lange etapper tilbakelegges med ulik fart."),wrong(f"{round(total/first_speed*60)} min","Du brukte den første farten på hele turen."),wrong(f"{round(total/second_speed*60)} min","Du brukte den andre farten på hele turen.")]
        steps=[f"Første halvdel er {nb_num(half,1)} km og tar {first_minutes} min.",f"Andre halvdel er {nb_num(half,1)} km og tar {second_minutes} min.",f"Totalt: {first_minutes} + {second_minutes} = {minutes} min."]
        builder.add(topic="Problemløsing",grade=grade_level(level),level=level,skill="fart og tid i flere etapper",qtype="challenge",
                    prompt=f"En tur er {total} km. Den første halvparten tilbakelegges i {first_speed} km/t og den andre halvparten i {second_speed} km/t. Hvor lang tid tar turen?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Turen tar {minutes} minutter.",tags=["fart","flere steg"])

    # 8 fraction/proportion inverse problems
    cases=[(2,5,18),(3,4,21),(5,8,15),(7,10,12),(3,7,24),(4,9,25),(5,12,28),(7,15,32)]
    for i,(used_n,den,left) in enumerate(cases):
        left_frac=Fraction(den-used_n,den)
        # adjust left to make whole integer
        multiplier=8+i
        left=left_frac.numerator*multiplier
        whole=left*left_frac.denominator//left_frac.numerator
        level=6+i//2; correct=str(whole)
        ws=[wrong(str(left*den//used_n if left*den%used_n==0 else left*den),"Du brukte den brukte brøkdelen på mengden som er igjen."),wrong(str(left),"Dette er bare resten."),wrong(str(whole-left),"Dette er mengden som ble brukt, ikke hele mengden.")]
        steps=[f"Når {used_n}/{den} er brukt, er {left_frac.numerator}/{left_frac.denominator} igjen.",f"{left_frac.numerator}/{left_frac.denominator} tilsvarer {left}.",f"Hele mengden er {whole}."]
        visual={"type":"fractionBar","numerator":left_frac.numerator,"denominator":left_frac.denominator,"label":"igjen"}
        builder.add(topic="Problemløsing",grade=grade_level(level),level=level,skill="finne helhet fra rest",qtype="challenge",
                    prompt=f"{used_n}/{den} av en samling er brukt. Det er {left} igjen. Hvor mange var det først?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Det var {whole} først.",visual=visual,tags=["brøk","omvendt problem"])

    # 7 geometry real-world
    cases2=[(8,6,2),(12,9,3),(15,10,2.5),(20,12,4),(9,6,1.5),(18,12,3),(25,15,5)]
    for i,(L,W,tile) in enumerate(cases2):
        area=L*W; tiles=area/(tile*tile); level=5+i//2; correct=nb_num(tiles,0)
        ws=[wrong(nb_num(area/tile,0),"En flis dekker et areal på side · side, ikke bare én sidelengde."),wrong(nb_num(area,0),"Dette er gulvarealet, ikke antall fliser."),wrong(nb_num(2*(L+W)/tile,0),"Dette regner langs kanten, men flisene skal dekke hele gulvet.")]
        steps=[f"Gulvareal: {L} · {W} = {area} m².",f"Én flis dekker {nb_num(tile*tile,2)} m².",f"Antall fliser: {area} ÷ {nb_num(tile*tile,2)} = {nb_num(tiles,0)}."]
        visual={"type":"tiledRectangle","length":L,"width":W,"tile":tile}
        builder.add(topic="Problemløsing",grade=grade_level(level),level=level,skill="areal i praktisk situasjon",qtype="challenge",
                    prompt=f"Et gulv er {L} m × {W} m. Kvadratiske fliser har side {nb_num(tile,1)} m. Hvor mange hele fliser trengs uten svinn?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Det trengs {correct} fliser.",visual=visual,tags=["geometri","areal"])

    # 6 combinations/logic
    combos=[(3,4),(4,5),(5,6),(3,7),(6,4),(5,8)]
    for i,(tops,bottoms) in enumerate(combos):
        ans=tops*bottoms; level=5+i; correct=str(ans)
        ws=[wrong(str(tops+bottoms),"Du la sammen valgene. Hver overdel kan kombineres med hver underdel."),wrong(str(ans-tops),"Du mangler kombinasjonene for én underdel."),wrong(str(ans+bottoms),"Du har telt én overdel for mye.")]
        steps=[f"For hver av {tops} overdeler finnes {bottoms} valg av underdel.",f"{tops} · {bottoms} = {ans} kombinasjoner."]
        visual={"type":"combinationGrid","rows":tops,"cols":bottoms}
        builder.add(topic="Problemløsing",grade=grade_level(level),level=level,skill="systematisk opptelling",qtype="standard",
                    prompt=f"Du har {tops} overdeler og {bottoms} underdeler. Hvor mange ulike antrekk kan du lage?",
                    correct=correct,wrongs=ws,explanation_steps=steps,takeaway=f"Det er {ans} kombinasjoner.",visual=visual,tags=["kombinatorikk"])

    # 6 hard mixed challenges
    hard = [
        {"start": Fraction(2,5), "end": Fraction(4,5), "added": 18, "unit": "L",
         "prompt": "En tank er 2/5 full. Etter at 18 liter fylles på, er den 4/5 full. Hvor mye rommer tanken?"},
        {"start": Fraction(3,8), "end": Fraction(5,8), "added": 75, "unit": "sider",
         "prompt": "Jens har lest 3/8 av en bok. Etter at han leser 75 sider til, har han lest 5/8. Hvor mange sider har boka?"},
        {"start": Fraction(1,3), "end": Fraction(2,3), "added": 28, "unit": "km",
         "prompt": "En syklist har fullført 1/3 av en rute. Etter 28 km til har hun fullført 2/3. Hvor lang er hele ruta?"},
        {"start": Fraction(5,12), "end": Fraction(3,4), "added": 42, "unit": "kasser",
         "prompt": "Et lager er fylt til 5/12 av kapasiteten. Når 42 kasser settes inn, er det 3/4 fullt. Hvor mange kasser rommer lageret?"},
        {"start": Fraction(7,15), "end": Fraction(11,15), "added": 32, "unit": "L",
         "prompt": "En beholder er 7/15 full. Etter at 32 liter fylles på, er den 11/15 full. Hvor mye rommer beholderen?"},
        {"start": Fraction(3,10), "end": Fraction(4,5), "added": 45, "unit": "km",
         "prompt": "En syklist har tilbakelagt 3/10 av en løype. Etter 45 km til har hun tilbakelagt 4/5. Hvor lang er hele løypa?"},
    ]
    for i, item in enumerate(hard):
        start_f = item["start"]
        end_f = item["end"]
        added = item["added"]
        unit = item["unit"]
        diff = end_f - start_f
        whole = Fraction(added, 1) / diff
        if whole.denominator != 1:
            raise AssertionError("Hard challenge must have integer whole")
        whole_i = whole.numerator
        level = 8 + i // 2
        correct = with_unit(whole_i, unit, 0)
        end_amount = int(whole_i * end_f)
        start_amount = int(whole_i * start_f)
        ws = [
            wrong(with_unit(added, unit, 0), "Dette er bare mengden som ble lagt til."),
            wrong(with_unit(end_amount, unit, 0), "Dette er mengden ved sluttbrøken, ikke hele mengden."),
            wrong(with_unit(start_amount, unit, 0), "Dette er mengden ved startbrøken, ikke hele mengden."),
        ]
        steps = [
            f"Endringen er {frac_text(end_f)} − {frac_text(start_f)} = {frac_text(diff)} av hele.",
            f"{frac_text(diff)} tilsvarer {added} {unit}.",
            f"Hele mengden er {whole_i} {unit}.",
        ]
        visual = {"type": "fractionTank", "start": frac_text(start_f), "end": frac_text(end_f), "added": added, "unit": unit}
        builder.add(topic="Problemløsing", grade=7, level=level, skill="avansert brøkproblem", qtype="challenge",
                    prompt=item["prompt"], correct=correct, wrongs=ws, explanation_steps=steps,
                    takeaway=f"Hele mengden er {correct}.", visual=visual, tags=["brøk", "utfordring"])


def validate_questions(questions: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    ids: set[str] = set()
    prompt_keys: set[str] = set()
    topic_counts: Counter[str] = Counter()
    grade_counts: Counter[int] = Counter()
    type_counts: Counter[str] = Counter()
    visual_counts: Counter[str] = Counter()
    level_counts: Counter[int] = Counter()

    for q in questions:
        qid = q.get("id")
        if qid in ids:
            errors.append(f"Duplicate id {qid}")
        ids.add(qid)
        key = (q["prompt"] + "|" + "|".join(o["text"] for o in q["options"])).lower()
        if key in prompt_keys:
            errors.append(f"Duplicate prompt/options {qid}")
        prompt_keys.add(key)
        if len(q["options"]) != 4:
            errors.append(f"{qid}: not four options")
        texts = [o["text"] for o in q["options"]]
        if len(set(texts)) != 4:
            errors.append(f"{qid}: duplicate options {texts}")
        ids_opts = [o["id"] for o in q["options"]]
        if q["correctOption"] not in ids_opts:
            errors.append(f"{qid}: correct option missing")
        for o in q["options"]:
            if o["id"] != q["correctOption"] and not o.get("feedback"):
                errors.append(f"{qid}: missing wrong feedback for {o['id']}")
        if not q["explanation"].get("steps"):
            errors.append(f"{qid}: no explanation steps")
        topic_counts[q["topic"]] += 1
        grade_counts[q["grade"]] += 1
        type_counts[q["type"]] += 1
        level_counts[q["level"]] += 1
        if q.get("visual"):
            visual_counts[q["visual"]["type"]] += 1

    for topic, target in TOPIC_TARGETS.items():
        if topic_counts[topic] != target:
            errors.append(f"{topic}: {topic_counts[topic]} != {target}")

    report = {
        "version": "1.0.0",
        "seed": SEED,
        "total": len(questions),
        "topics": dict(topic_counts),
        "grades": {str(k): v for k, v in sorted(grade_counts.items())},
        "levels": {str(k): v for k, v in sorted(level_counts.items())},
        "types": dict(type_counts),
        "visualQuestions": sum(visual_counts.values()),
        "visualTypes": dict(visual_counts),
        "errors": errors,
    }
    return report


def main() -> None:
    builder = BankBuilder()
    add_tall(builder)
    add_brok(builder)
    add_desimal(builder)
    add_prosent(builder)
    add_algebra(builder)
    add_geometri(builder)
    add_maling(builder)
    add_statistikk(builder)
    add_okonomi(builder)
    add_problemlosing(builder)
    builder.ensure_targets()

    report = validate_questions(builder.questions)
    if report["errors"]:
        raise SystemExit("Validation failed:\n" + "\n".join(report["errors"]))

    bank = {
        "version": "1.0.0",
        "title": "JENS MATTE 5.–7.",
        "curriculum": "LK20 MAT01-05",
        "generatedAt": "2026-10-20",
        "description": "500 originale flervalgsoppgaver for adaptiv matematikktrening på 5.–7. trinn.",
        "schemaVersion": 1,
        "questions": builder.questions,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
