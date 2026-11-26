"""Selftest determinista del módulo rubric_state (PROP-RUBRICA-VIVA-001, issue #17, paso 3)."""

import json
import sys
import unittest

sys.path.insert(0, "src")

from rubric_state import Rubric, RubricBook, RubricStatus


class TestRubric(unittest.TestCase):
    def test_dormancy_after_n_clean_streak(self):
        rubric = Rubric("R1", "lee el código antes de editar", clean_streak_threshold=3)
        events = [rubric.record(True) for _ in range(3)]
        self.assertEqual(rubric.status, RubricStatus.DORMANT)
        self.assertEqual(rubric.dormancies, 1)
        self.assertEqual(events[-1].event, "sleep")

    def test_streak_reset_on_fail_while_active(self):
        rubric = Rubric("R1", "ejecuta los tests antes de cerrar", clean_streak_threshold=3)
        rubric.record(True)
        rubric.record(True)
        rubric.record(False)
        self.assertEqual(rubric.status, RubricStatus.ACTIVE)
        self.assertEqual(rubric.clean_streak, 0)
        self.assertEqual(rubric.regressions, 1)

    def test_reactivation_on_regression_while_dormant(self):
        rubric = Rubric("R1", "verifica en la fuente (PROC-010)", clean_streak_threshold=2)
        rubric.record(True)
        rubric.record(True)
        self.assertEqual(rubric.status, RubricStatus.DORMANT)
        event = rubric.record(False)
        self.assertEqual(rubric.status, RubricStatus.ACTIVE)
        self.assertEqual(event.event, "reactivate")
        self.assertEqual(rubric.regressions, 1)

    def test_dormant_clean_pass_emits_no_signal(self):
        rubric = Rubric("R1", "regla canónica", clean_streak_threshold=1)
        rubric.record(True)
        self.assertEqual(rubric.status, RubricStatus.DORMANT)
        event = rubric.record(True)
        self.assertEqual(event.event, "noop")

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            Rubric("R1", "inválida", clean_streak_threshold=0)

    def test_reactivation_then_re_dormancy_cycle(self):
        rubric = Rubric("R1", "ciclo completo", clean_streak_threshold=2)
        for _ in range(2):
            rubric.record(True)
        self.assertEqual(rubric.status, RubricStatus.DORMANT)
        rubric.record(False)
        self.assertEqual(rubric.status, RubricStatus.ACTIVE)
        for _ in range(2):
            rubric.record(True)
        self.assertEqual(rubric.status, RubricStatus.DORMANT)
        self.assertEqual(rubric.dormancies, 2)


class TestRubricBook(unittest.TestCase):
    def _book(self, thresholds):
        book = RubricBook(scorer=lambda rid, trace: trace.get(rid, False))
        for i, t in enumerate(thresholds, start=1):
            book.add(Rubric(f"R{i}", f"criterio {i}", clean_streak_threshold=t))
        return book

    def test_mixed_book_signals(self):
        book = self._book([2, 5])
        for _ in range(3):
            signals = book.record_execution({"R1": True, "R2": True})
        self.assertEqual(book.rubrics["R1"].status, RubricStatus.DORMANT)
        self.assertEqual(book.rubrics["R2"].status, RubricStatus.ACTIVE)
        signals = book.record_execution({"R1": False, "R2": True})
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].event, "reactivate")
        self.assertEqual(signals[0].rubric_id, "R1")

    def test_snapshot_is_json_serializable(self):
        book = self._book([1, 2])
        book.record_execution({"R1": True, "R2": True})
        snapshot = book.snapshot()
        payload = json.dumps(snapshot)
        parsed = json.loads(payload)
        self.assertEqual(parsed["R1"]["status"], "dormant")
        self.assertIn("clean_streak_threshold", parsed["R2"])

    def test_duplicate_rubric_rejected(self):
        book = self._book([])
        book.add(Rubric("R1", "uno"))
        with self.assertRaises(ValueError):
            book.add(Rubric("R1", "duplicado"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
