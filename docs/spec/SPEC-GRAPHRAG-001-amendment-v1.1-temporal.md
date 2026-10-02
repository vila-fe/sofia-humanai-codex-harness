# SPEC-GRAPHRAG-001 — Enmienda v1.1: capa temporal (DEC-TGRAG-001)

**Estado:** Proposed (Candidate) — pendiente HITL AVF
**Fecha:** 2026-10-02 · **Origen:** DEC-TGRAG-001 (🟢 Aprobada 02/10/2026) · **Autor:** AVFrere (Vibe/Mistral, GLM-5), clave de sesión S-20261002-VIB

## 1. Motivo

El Carril B (grafo condicionado, Kuzu embebido) de SPEC-GRAPHRAG-001 v1.0 no distingue hechos vigentes de obsoletos. La recuperación puede entregar al LLM decisiones o estados superados (p. ej. un gate REMEDIATED cuando ya está CERRADO). Fuente del patrón: «Adding Temporal Reasoning to Graph-RAG» (MachineLearningMastery, 01/10/2026); contraste: arXiv 2510.13590 (TG-RAG), arXiv 2509.19376 (límites del freshness-boosting heurístico).

## 2. Cambios sobre v1.0 (Carril B)

1. **Cuádruplas:** toda arista del grafo lleva `timestamp` obligatorio (procedente del Bloque de Procedencia, DEC-TRAZ-REG-001 v1.1 — cero infraestructura nueva). Nodo: `timestamp` recomendado.
2. **Peso de recencia (mecanismo por defecto):** `w = 2^(-(h(tipo)·Δt))` con semivida h por tipo de nodo. Valores iniciales (hipótesis a calibrar en mini-bench as-of): Decisiones 90 d · Episodios 60 d · Fichas Radar 14 d · Bloques MEM-KORE §1 30 d.
3. **Ventanas de validez (alternativa determinista):** campos reservados `valid_from`/`valid_to` en aristas; se derivan por supersesión (cada hecho vigenta hasta el siguiente del mismo atributo de entidad). Selección de mecanismo: mini-bench as-of (gate G-TGRAG-BENCH, HITL).
4. **Ranking as-of en consulta:** antes de pasar contexto al LLM, los hechos en conflicto se ordenan por peso (o se filtran por ventana) según la fecha de consulta; el LLM recibe solo el hecho vigente.
5. **Regla de fecha desconocida:** hecho sin timestamp → peso 0 y bandera `unknown_date`; nunca se pondera silenciosamente.
6. **Configuración externa:** semividas en `config/temporal_half_lives.yaml` — recalibrables sin tocar código.

## 3. No-cambios

- Carril A (híbrida BM25+vector+reranker) sin cambios.
- No se re-implementa MS GraphRAG; no se añade dependencia nueva (Kuzu embebido ya previsto).
- Gates GB-0..GB-5 de v1.0 se mantienen; esta enmienda añade G-TGRAG-BENCH (selección de mecanismo) y G-TGRAG-TEST (tests).

## 4. Gates nuevos

| Gate | Contenido | Tipo |
|---|---|---|
| G-TGRAG-BENCH | Mini-bench as-of ≥10 preguntas reales; precisión ≥70%; selección decaimiento vs ventanas | HITL |
| G-TGRAG-TEST | Unitarios + integración + re-bench sin regresión; 100% aristas con timestamp | HITL |

## 5. Trazabilidad

- DEC-TGRAG-001 (Notion, Decisiones SOFIA): condiciones de ejecución.
- Implementación: `vila-fe/sofia-twin-digital-avf` rama `tgrag-001-temporal-recency`.
- Informe de análisis: Canvas «Análisis SOFIA — Razonamiento temporal en Graph-RAG» (02/10/2026).
