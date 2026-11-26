# SPEC-RUBRICA-VIVA-001 — Guion del paso 4: veredicto con episodios históricos (piloto rúbricas vivas, issue #17)

**Bloque de Procedencia (DEC-TRAZ-REG-001 v1.1):** Origen registro: Vibe/Mistral (AVFrere-c, GLM-5.3) · 2026-11-26 · Clave: S-20261126-VIB · Propósito: materializar el guion de verificación (paso 4) del prototipo `src/rubric_state.py` (pasos 2-3, PR #18) según el plan del issue #17, con método científico en sandbox y presupuesto frugal · Padre: informe Radar S-20261126-VIB (vila-fe/sofia-human-ai-avf#91) · Supervisión: HOOTL (ejecución del guion), HITL para todo cambio de esquema Supabase.

## 1. Objetivo y preguntas operativas

Validar la máquina de estados de rúbrica viva (ACTIVE/DORMANT, dormancia a N, reactivación en 1 regresión) con **trazas reales** en lugar de sintéticas:

- Q1 ¿El estado persistido en `evaluation_metrics.evaluator_context` sobrevive a ejecuciones separadas sin pérdida?
- Q2 ¿El scorer por criterio sobre episodios históricos del harness discrimina (no colapsa a todo-verde)?
- Q3 ¿La dormancia reduce señal redundante sin ocultar regresiones reales?

## 2. Precondiciones (verificar en vivo, PROC-010 — no asumir)

| # | Precondición | Verificación | Estado |
|---|---|---|---|
| P1 | Las tablas Supabase `agent_sessions`, `implementations`, `evaluation_metrics`, `reasoning_traces` existen y aceptan escritura | SQL en vivo en el perímetro autorizado (gemelo/psql). **Fricción conocida:** hallazgo D4 del Informe del Clúster 11/11 las declaró inexistentes; el README asume el esquema desplegado. En caso de no existir: veredicto se limita al modo offline (P5) y se abre MNT | Pendiente |
| P2 | Hay episodios históricos con `evaluation_metrics` suficientes (≥ 30 evaluaciones para un umbral N=10) | SQL count | Pendiente |
| P3 | Acceso a Supabase desde el perímetro del sandbox | Conector o psql en perímetro gemelo | Pendiente (sin conector en Vibe, sesión 26/11) |

## 3. Experimentos E1-E5 (criterios PASS/FAIL)

| # | Experimento | PASS | FAIL |
|---|---|---|---|
| E1 | Replayed dormancy: alimentar la rúbrica con la serie histórica de un criterio real y comprobar transiciones | Las transiciones observadas (sleep/reactivate) coinciden con las esperadas por los resultados de la serie; 0 transiciones fantasma | Transiciones espurias o estados inconsistentes |
| E2 | Persistencia round-trip: `snapshot()` → `evaluator_context` (JSON) → reconstrucción → nueva ejecución | Estado idéntico tras round-trip (contadores, status, umbral); JSON ≤ 2 KB por rúbrica | Pérdida de contadores o estado alterado |
| E3 | Discriminación del scorer: distribución de resultados por criterio sobre ≥ 30 evaluaciones reales | Al menos un criterio con mezcla real de éxitos/fallos (no colapsa a 100 % verde) | Todos los criterios al 100 % (scorer trivial: no mide nada) |
| E4 | Utilidad de dormancia: volumen de señal emitida con y sin dormancia sobre la misma serie | Señal reducida ≥ 50 % sin pérdida de regresiones detectadas (recall = 1,0 sobre regresiones de la serie) | Cualquier regresión de la serie no detectada, o señal sin reducción |
| E5 | Determinismo: 3 ejecuciones de E1-E4 con la misma entrada | Salidas idénticas byte a byte | Cualquier divergencia |

## 4. Veredicto y destino

- **PASS (E1-E5):** la rúbrica viva queda promotible a candidate de integración en el bucle agéntico (`AgenticLoopWithMemory`), gate HITL de AVF; claim a UC/Wiki por la vía canónica (lote + PR).
- **FAIL parcial (solo P1 caída):** modo offline — el guion se ejecuta con trazas exportadas en JSONL estacionadas en RAW Vault; veredicto provisional clase b; MNT abierta para el esquema Supabase.
- **FAIL estructural (E4/E5):** el prototipo se archiva como experimento negativo con informe de fricción a la Cola MNT; el patrón RuHarness queda en vigilancia Radar, no en adopción.

## 5. Presupuesto y reglas

- Escrituras: ≤ 3 (SPEC en GitHub, comentario de veredicto en #17, lote UC claim si PASS).
- Frugalidad: 0 € de APIs; stdlib pura; sin red en sandbox (las consultas SQL se ejecutan en el perímetro autorizado y su salida se estaciona como JSONL).
- Reversibilidad: total; el prototipo no toca rutas operativas del bucle vigente.
- Regla de cálculo diferencial (§10 arranque v0.4.2): ciclos E1-E5 solo se repiten si el incremento estimado supera el 10 %; el cese se declara explícitamente.
