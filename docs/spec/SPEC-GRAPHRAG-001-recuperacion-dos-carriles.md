# SPEC-GRAPHRAG-001 — Recuperación de dos carriles (híbrida + grafo) para WIKI SOFIA

**Programa SOFIA Human-AI AVFEARS · v1.0 · 25/09/2026 · Autor: AVFrere**
**Estado:** Approved (base de dos carriles aprobada por HITL AVF, 25/09/2026). GitHub = fuente de verdad.
**Basis:** EP-2026-09-25-C (piloto estándar SO-SR v0.2, evidencia E1-E10) · PROC-012 · AtomRAG (EP-2026-09-14-M)

## 1. Objetivo y alcance

Especificar la arquitectura de recuperación de la WIKI SOFIA (corpus federado: MEM-KORE, Episodios, Decisiones, Skills, Wiki Drive, RAW Vault) con **dos carriles complementarios**, activación condicionada del carril de grafo, y presupuesto frugal. No cubre: ingesta (GESCOLA), ni el motor LLM (Router SOFIA / OpenRouter, ver EP-2026-09-25-B).

## 2. Arquitectura de dos carriles

### Carril A — Híbrida vectorial (base, siempre activa)

1. **Chunking:** recursive, 512-1024 tokens, **sin overlap** (E5: el overlap no aporta beneficio medible, arXiv ene-2026; E6: hasta 9% de brecha de recall entre estrategias).
2. **Embedding:** modelo multilingüe Hugging Face validado en PROC-012 (ganó sobre 39 decisiones reales).
3. **Recuperación paralela:** BM25/TF-IDF (sparse) + ANN vectorial (dense) — E7.
4. **Fusión:** RRF (Reciprocal Rank Fusion), no combinación lineal de scores — E7.
5. **Reranking:** cross-encoder sobre el top-K fusionado (nunca sobre el corpus completo) — E7.
6. **Scaffolding de consulta:** descomposición atómica tipo AtomRAG para consultas complejas (E10: scaffolding > retrieval con mismo recall).

**Cubre:** lookup puntual (E2: en consultas single-hop el grafo pierde 13,4% frente al vectorial).

### Carril B — Grafo (condicionado, activación por medición)

1. **Origen de nodos (principio frugal rector):** SOFIA **no re-implementa** el pipeline GraphRAG de Microsoft. Los nodos de grafo se generan como **subproducto del protocolo SO-SR** (grafo de citas autor->referencia->extensión) y de las **relaciones estructurales ya existentes** en Notion (DEC->PROP->EP->gemelos->patrones).
2. **Formato de nodo (contrato de datos, alineado con sofia_trazabilidad):**
```yaml
nodo_id: UUID
tipo: [entidad | decision | propuesta | episodio | patron | cita | fuente]
etiqueta: texto
relaciones: [{destino: nodo_id, tipo_relacion: texto, vigencia: fecha}]
metadatos: {fecha_origen, confianza, alcance, vigencia, uri_persistencia, costo_tokens_est}
chunk_vectorial: [chunk_ids del carril A]  # enlace dual carril A<->B
```
3. **Almacén de grafo:** base embebida sin servidor (Kuzu o equivalente embebible; E8). Alternativa agnóstica: BigQuery para el índice vectorial.
4. **Presupuesto de coste (E3, E4):** indexación vectorial 10k docs <5 USD; el pipeline de grafo completo costaría 50-200 USD — **evitado por diseño** (nodos subproducto, sin extracción LLM masiva). Selección dinámica de comunidades solo si se añade resumen jerárquico (-77% tokens, E4).

**Cubre:** consultas multi-hop y síntesis temática transversal (E1: 86% vs 32%).

## 3. Mini-bench de activación del Carril B

- **Muestra:** >=50 consultas reales representativas (logs de sesiones AVFrere + preguntas tipo del programa).
- **Clasificación:** cada consulta etiquetada como lookup / multi-hop / síntesis temática.
- **Umbral de activación:** >=20% de consultas multi-hop/síntesis (criterio aprobado con la base de dos carriles).
- **Métrica de calidad:** top-5 accuracy >=70% sobre 50 queries (alineado GATE B3); latencia <=5 s en máquina 8 GB (GATE B4).
- **Referencia externa:** GraphRAG-Bench/HopRAG (2026) si se necesita comparabilidad (E8).
- **Ejecución:** HOOTL una vez construido el log; resultado registrado como Decisión SOFIA.

## 4. Enrutado de consultas

1. Clasificador barato de intención (lookup vs multi-hop) — heurístico por prompt del LLM de sesión (capa 1 Router SOFIA).
2. Lookup -> Carril A. Multi-hop/síntesis -> Carril B (si activo) con fallback a Carril A + AtomRAG.
3. Respuestas del Carril B citan nodos con uri_persistencia (trazabilidad AI Act; fuente mínima).

## 5. Presupuesto y gobernanza

- **CaseEnvelope de indexación:** cada reindexación masiva exige presupuesto explícito; por defecto 5 EUR / 120 min / 1 retry (evidencia E3).
- **Supervisión:** construcción/mantenimiento HOOTL una vez auditado; activación del Carril B y cambios del SPEC: HITL AVF; mini-bench: HOOTL con registro en Decisiones.
- **Regla de no-duplicación:** MEM-KORE (Notion) es la fuente de verdad; los carriles son índices de recuperación, no almacenes canónicos. Precedencia: MEM-KORE > Wiki > intersesión.
- **Trazabilidad AI Act:** toda respuesta RAG declara nodos/chunks citados; divulgación de uso de IA por etapa.

## 6. Gates de implementación (alineados con W0-W6)

| Gate | Criterio de paso |
|---|---|
| GB-0 | Corpus mínimo Carril A: >=100 docs (alineado GATE B2) + sync Notion<->Drive completada |
| GB-1 | Top-5 accuracy >=70% en 50 queries reales (Carril A) |
| GB-2 | Mini-bench de distribución ejecutado y registrado (sección 3) |
| GB-3 | Decisión HITL de activación del Carril B (>=20% multi-hop) |
| GB-4 | Si activo: Carril B responde multi-hop con >=2 nodos citados por respuesta; latencia <=10 s |
| GB-5 | Auditoría trimestral de coherencia MEM-KORE <-> índices |

## 7. Dependencias y riesgos

- **Depende de:** G2 de SOFIA-RECUPERA (parseo/validación del corpus), sincronización Notion<->Drive pendiente, Silo Perplexity (REM-05).
- **Riesgo principal (stress-test):** activar el Carril B antes del corpus mínimo = infraestructura antes que datos. Mitigado por GB-0 y GB-2.
- **Riesgo secundario:** deriva de duplicación índice<->canónico. Mitigado por regla de no-duplicación y GB-5.

## 8. Siguientes pasos

1. GB-0: completar G2 SOFIA-RECUPERA + sincronización Wiki.
2. Prototipo del clasificador de nodos a partir de relaciones DEC/PROP/EP existentes (en sofia-twin-digital-avf).
3. Ejecutar mini-bench (GB-2) -> decisión HITL (GB-3).
