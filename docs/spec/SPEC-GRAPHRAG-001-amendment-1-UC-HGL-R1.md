# SPEC-GRAPHRAG-001 — Enmienda 1: incorporación de DEC-UC-HGL-R1 (mini-bench GB-3 y Carril B)

**Estado:** Aprobada por AVF 05/10/2026 (gate HITL, sesión S-20261005)
**Decisión de origen:** DEC-UC-HGL-R1 (Notion, Decisiones SOFIA — Trazabilidad HITL, 2026-10-05)
**Espec base:** SPEC-GRAPHRAG-001 v1.0 (commit db768425, docs/spec/)

> Nota: enmienda como archivo independiente; la spec original no se modifica (vive en su propio historial). Fusionar en la próxima iteración de la spec (v1.1).

## 1. Cambio en el gate GB-3 (mini-bench)

El mini-bench de ≥50 consultas reales definido para GB-3 obtiene ahora **doble función formal**:

1. **Función existente:** decidir la activación del Carril B (grafo condicionado, Kuzu embebido) — umbral ≥20% de consultas multi-hop.
2. **Función nueva (DEC-UC-HGL-R1):** el mismo mini-bench y el mismo umbral gobiernan el **escalado de la Unidad Cognitiva** a arquitectura de grafo multiagente. No se duplica infraestructura de evaluación: una sola medición, dos gates.

**Criterio de medición multi-hop:** una consulta cuenta como multi-hop si la cadena óptima de recuperación requiere ≥2 saltos entre nodos de distinto tipo (ej. episodio→decisión→átomo, decisión→episodio→decisión).

**Protocolo anti-trampa (nuevo):** durante el mini-bench, cualquier rama que convierta una comprobación determinista en llamada secuencial al LLM se marca como violación UC-HGL-R1 y se reporta en el resultado del gate.

## 2. Cambio en el diseño de la Carril B / UC

Mientras el umbral (≥20% multi-hop en ≥50 consultas) no se alcance:

- La UC opera como **loop bien diseñado dentro del harness existente** (MEM-KORE + recuperación híbrida Carril A + enjambre MacQAS atomizado por DEC-MEM-ATOMO-001).
- **Prohibido:** orquestador-worker, handoffs entre nodos LLM, fan-out paralelo de agentes.
- **Permitido:** routers deterministas para categorías exactas (no llamadas LLM).

Al alcanzar el umbral, el escalado requiere gate HITL explícito de AVF (no automático).

## 3. Re-evaluación

Ante upgrade de modelo del stack, re-evaluar la regla: los modelos se sobreajustan a harnesses propietarios (RADAR-T-2026-W41-H13, fuente: Rastogi 04/08/2026, EP-2026-10-04-I ALTO-CRÍTICO).

## Bloque de Procedencia (DEC-TRAZ-REG-001 v1.1)

- **Origen registro:** AVFrere (Vibe/GLM) vía GitHub App
- **Fecha-hora registro:** 2026-10-05T14:10:00 Europe/Madrid
- **Propósito:** incorporar DEC-UC-HGL-R1 al mini-bench GB-3 de SPEC-GRAPHRAG-001 y a la condición del Carril B, por encargo de AVF del 05/10/2026
- **Clave de sesión:** S-20261005-AVF
