"""Experimentos offline del SPEC-RUBRICA-VIVA-001 (issue #17, paso 4, modo offline).

E2 — persistencia round-trip: snapshot() -> JSON (evaluator_context) ->
     reconstruccion -> nueva ejecucion; el estado debe sobrevivir.
E5 — determinismo: 3 ejecuciones de la misma serie producen salidas identicas.

Uso: python3 scripts/rubric_exp_offline.py  (imprime veredicto E2/E5, exit 0/1)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubric_state import Rubric, RubricBook, RubricStatus

SERIE = [True, True, True, True, True, True, True, True, False,
         True, True, True, True, True, True, True, True, False,
         True, True, True, True, True, True, True, True, True, True]


def build_book():
    book = RubricBook(scorer=lambda rid, trace: trace[rid])
    book.add(Rubric("E2-R1", "round-trip", clean_streak_threshold=10))
    return book


def run_series(book):
    signals = []
    for i, result in enumerate(SERIE):
        trace = {"E2-R1": result}
        for event in book.record_execution(trace):
            signals.append((i, event.event, event.detail))
    return signals


def exp_e2_roundtrip():
    book = build_book()
    run_series(book)
    payload = json.dumps(book.snapshot())
    rebuilt = RubricBook(scorer=lambda rid, trace: trace[rid])
    for rid, data in json.loads(payload).items():
        rebuilt.add(Rubric(rid, data["description"],
                           status=RubricStatus(data["status"]),
                           clean_streak=data["clean_streak"],
                           regressions=data["regressions"],
                           dormancies=data["dormancies"],
                           clean_streak_threshold=data["clean_streak_threshold"]))
    ok = (
        rebuilt.rubrics["E2-R1"].status is book.rubrics["E2-R1"].status
        and rebuilt.rubrics["E2-R1"].clean_streak == book.rubrics["E2-R1"].clean_streak
        and rebuilt.rubrics["E2-R1"].regressions == book.rubrics["E2-R1"].regressions
        and rebuilt.rubrics["E2-R1"].dormancies == book.rubrics["E2-R1"].dormancies
        and len(payload) <= 2048
    )
    return ok, payload


def exp_e5_determinism():
    outputs = []
    for _ in range(3):
        book = build_book()
        signals = run_series(book)
        outputs.append(json.dumps({"signals": signals, "snapshot": book.snapshot()}, sort_keys=True))
    return len(set(outputs)) == 1, outputs[0]


def main():
    e2_ok, payload = exp_e2_roundtrip()
    e5_ok, sample = exp_e5_determinism()
    print(f"E2 round-trip: {'PASS' if e2_ok else 'FAIL'} (payload {len(payload)} bytes)")
    print(f"E5 determinismo: {'PASS' if e5_ok else 'FAIL'} (3 ejecuciones identicas)")
    verdict = e2_ok and e5_ok
    print(f"Veredicto offline E2/E5: {'PASS' if verdict else 'FAIL'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
