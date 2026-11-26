"""
RubricState — rúbricas vivas para el módulo de Gestión de Fricciones (piloto PROP-RUBRICA-VIVA-001, issue #17).

Patrón RuHarness (AI Engineering 26/11/2026): los criterios de evaluación
evolucionan con las trazas — un criterio se duerme tras N ejecuciones limpias
consecutivas y se reactiva ante una regresión. El objetivo de la tarea
permanece fijo; solo cambia qué criterios diagnostican.

Diseño (paso 2 del issue #17), stdlib puro y determinista, sin red:
- Estados: ACTIVE (puntúa cada ejecución) y DORMANT (no puntúa, solo vigila
  regresión).
- Dormancia: N éxitos consecutivos (clean_streak_threshold).
- Reactivación: 1 fallo durante DORMANT reactiva a ACTIVE y registra una
  señal de regresión.
- Registro: cada transición y cada resultado emiten un evento para
  persistencia en `evaluation_metrics.evaluator_context` (esquema Supabase
  ya asumido por PersistentMemory, sin cambios de esquema).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RubricStatus(Enum):
    ACTIVE = "active"
    DORMANT = "dormant"


@dataclass
class RubricEvent:
    rubric_id: str
    event: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rubric:
    rubric_id: str
    description: str
    status: RubricStatus = RubricStatus.ACTIVE
    clean_streak: int = 0
    regressions: int = 0
    dormancies: int = 0
    clean_streak_threshold: int = 10
    events: List[RubricEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.clean_streak_threshold < 1:
            raise ValueError("clean_streak_threshold debe ser >= 1")

    def _emit(self, event: str, detail: Dict[str, Any]) -> None:
        self.events.append(RubricEvent(self.rubric_id, event, detail))

    def record(self, passed: bool) -> RubricEvent:
        """Registra el resultado de una ejecución y devuelve el evento de transición (o None)."""
        if passed:
            self.clean_streak += 1
            if (
                self.status is RubricStatus.ACTIVE
                and self.clean_streak >= self.clean_streak_threshold
            ):
                self.status = RubricStatus.DORMANT
                self.dormancies += 1
                self.clean_streak = 0
                self._emit(
                    "sleep",
                    {"dormancies": self.dormancies, "clean_streak_threshold": self.clean_streak_threshold},
                )
                return self.events[-1]
            return RubricEvent(self.rubric_id, "noop", {"clean_streak": self.clean_streak})
        self.regressions += 1
        if self.status is RubricStatus.DORMANT:
            self.status = RubricStatus.ACTIVE
            self.clean_streak = 0
            self._emit(
                "reactivate",
                {"regressions": self.regressions},
            )
            return self.events[-1]
        self.clean_streak = 0
        return RubricEvent(self.rubric_id, "fail", {"regressions": self.regressions})


@dataclass
class RubricBook:
    """Conjunto de rúbricas de un proyecto; extiende el papel del evaluator_context."""
    rubrics: Dict[str, Rubric] = field(default_factory=dict)
    scorer: Optional[Callable[[str, Dict[str, Any]], bool]] = None

    def add(self, rubric: Rubric) -> None:
        if rubric.rubric_id in self.rubrics:
            raise ValueError(f"rubric_id duplicado: {rubric.rubric_id}")
        self.rubrics[rubric.rubric_id] = rubric

    def record_execution(self, trace: Dict[str, Any]) -> List[RubricEvent]:
        """Evalúa las rúbricas activas contra una traza de ejecución y devuelve las señales."""
        signals: List[RubricEvent] = []
        for rubric in self.rubrics.values():
            if self.scorer is None:
                raise ValueError("scorer no definido; no se puede evaluar la traza")
            if rubric.status is RubricStatus.DORMANT:
                passed = self.scorer(rubric.rubric_id, trace)
                if passed:
                    continue
                event = rubric.record(False)
                signals.append(event)
                continue
            passed = self.scorer(rubric.rubric_id, trace)
            event = rubric.record(passed)
            if event.event == "sleep":
                signals.append(event)
        return signals

    def snapshot(self) -> Dict[str, Any]:
        """Serializable a `evaluation_metrics.evaluator_context` de PersistentMemory."""
        return {
            rubric.rubric_id: {
                "description": rubric.description,
                "status": rubric.status.value,
                "clean_streak": rubric.clean_streak,
                "regressions": rubric.regressions,
                "dormancies": rubric.dormancies,
                "clean_streak_threshold": rubric.clean_streak_threshold,
            }
            for rubric in self.rubrics.values()
        }
