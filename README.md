# sofia-humanai-codex-harness

**SOFIA Human-AI + Codex Harness Framework** — componente reusable del **Programa SOFIA
Human-AI AVFEARS** para dar memoria persistente entre sesiones a bucles agénticos de codificación
("Codex Harness"): agentes que ejecutan tareas de código de forma iterativa y necesitan recordar
qué se implementó, cómo se evaluó, y por qué se tomó cada decisión, más allá de una sola sesión.

Licencia: Apache 2.0. Único repo público del stack SOFIA — pensado para ser reusable fuera del
programa, no solo como documentación interna.

## Qué hace

Inspirado en la arquitectura AVO de Nvidia (memoria persistente + supervisor), expone dos
piezas en [`src/persistent_memory.py`](src/persistent_memory.py):

- **`PersistentMemory`** — capa de persistencia sobre Supabase. Guarda sesiones de agente,
  implementaciones (con hash de contenido para deduplicar), métricas de evaluación, y trazas de
  razonamiento paso a paso (decisión, justificación, alternativas rechazadas). Permite recuperar
  sesiones similares por firma de tarea (`retrieve_relevant`) para enriquecer el contexto de una
  nueva ejecución con trabajo previo.
- **`AgenticLoopWithMemory`** — envuelve un bucle agéntico completo: al arrancar recupera
  sesiones relevantes, en cada paso registra traza + artefacto + métricas
  (`execute_step`), y detecta estancamiento (`check_supervisor_signals`: si las últimas *N*
  evaluaciones no mejoran, emite una señal de `stagnation_detected` para que el supervisor
  redirija la estrategia) antes de cerrar la sesión con coste y latencia agregados
  (`finalize_session`).

## Uso mínimo

```python
from persistent_memory import PersistentMemory, AgenticLoopWithMemory

memory = PersistentMemory(supabase_url=..., supabase_key=...)
loop = AgenticLoopWithMemory(memory, project_id="sofia-router", task_signature="fix-circuit-breaker")

loop.start_session(model_used="claude-sonnet-5")
loop.execute_step(
    decision_type="fix",
    decision_text="Ajustar umbral del circuit breaker",
    implementation_content="<diff o código>",
    evaluation_metrics={"tests_passing": 1.0},
)
if loop.check_supervisor_signals() == "stagnation_detected":
    ...  # redirigir estrategia
loop.finalize_session(success_flag=True, total_cost_usd=0.02, avg_latency_ms=450)
```

Requiere un esquema Supabase con las tablas `agent_sessions`, `implementations`,
`evaluation_metrics`, `reasoning_traces`, y la función RPC `find_similar_sessions` (no incluidos
en este repo — se asume desplegados en el proyecto Supabase del Programa SOFIA).

## Estado

Repo joven (2 commits, 21-22/08/2026) pero con código real y funcional, no solo diseño. Sin
tests ni CI configurados todavía.
