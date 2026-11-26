---
name: hfe-suelo-evaluacion
description: >-
  Skill del stack SOFIA (MacQAS Atómico · llm-as-a-verifier) para cargar y
  evaluar la fiabilidad de suelo de un modelo con la suite Suelo HFE
  (Humanity's First Exam de Google DeepMind): descarga asistida del dataset
  Kaggle deepmind/hfe-public (112 prompts, CC BY 4.0), ingesta automática al
  formato de la suite, métricas pass@1 / family-pass con cota Wilson 95%,
  umbral canónico de suelo y registro de política JSONL. Disparadores:
  "carga los prompts HFE", "evalúa el suelo", "suelo HFE".
version: v0.1 (CANDIDATO)
padre: llm-as-a-verifier#3 (Suelo HFE)
componentes: llm_verifier/hfe_floor.py · scripts/ingest_hfe_public.py · scripts/run_hfe_floor.py · criteria/hfe_floor.md · data/hfe_floor_trajs/hfe_taxonomy.json
---

# hfe-suelo-evaluacion — Suelo HFE (fiabilidad de suelo) v0.1

Skill que operativiza la recomendación AVFrere-b/c (impacto de *Humanity's
First Exam* para SOFIA): mide si un modelo responde preguntas elementales
correctamente **cada vez** y ante variantes de reformulación — el criterio de
umbral de confianza de la Gestión de Fricciones y el Reglamento Canónico.

## 1. Cuándo se usa
- Cargar los 112 prompts públicos de HFE y validar la suite en HOOTL.
- Evaluar el suelo de un modelo antes de promoverlo entre entornos (MacQAS).
- Revisar fricciones tipo "variación de prompt" con métrica family-pass.

## 2. Pipeline (5 pasos, DEC-VIA-SCRIPTS-001: vía canónica por scripts)

| Paso | Acción | Gate | Herramienta |
|---|---|---|---|
| 1 | Descarga manual del zip: https://www.kaggle.com/datasets/deepmind/hfe-public | **HITL humano** (Kaggle exige sesión; sin acceso automatizado posible — verificado 26/11/2026) | Navegador de AVF |
| 2 | Entrega del zip al repo: `data/hfe_floor_trajs/kaggle_raw/` de `vila-fe/llm-as-a-verifier` (o pegado del JSONL/CSV en el chat) | HOTL | GitHub upload / chat |
| 3 | Ingesta: `python scripts/ingest_hfe_public.py data/hfe_floor_trajs/kaggle_raw/<zip> --run` (autodetecta zip/dir/JSONL/CSV/Harbor; esperado: 112 prompts, 28 familias) | HOOTL | scripts/ingest_hfe_public.py |
| 4 | Validación HOOTL + registro de política: `python scripts/run_hfe_floor.py --suite data/hfe_floor_trajs/hfe_public_floor.jsonl` — umbral canónico 0.85 sobre la cota inferior Wilson del family-pass; cada ejecución anota `data/progress_tracking/hfe_floor_log.jsonl` | HOOTL | scripts/run_hfe_floor.py |
| 5 | Evaluación con verificador sobre trayectorias reales: `python scripts/run.py hfe_floor` (cuando existan trayectorias de modelos bajo test) | HOTL | llm-as-a-verifier pipeline |

## 3. Métrica y umbral canónico
- **pass@1**: fracción de runs individuales correctos.
- **family-pass**: fracción de familias con TODOS los miembros y TODOS los
  runs correctos (la métrica estricta de HFE; análoga a family pass₄ 4×4).
- **Veredicto**: PASS solo si la **cota inferior Wilson 95%** del family-pass
  ≥ umbral 0.85. Con familias visuales, filtrar por `capability` antes de
  concluir sobre modelos text-only (gestión de sesgos multimodales).
- Los `capability` de la suite usan los ids de la taxonomía canónica HFE
  (`hfe_taxonomy.json`, 20 subcategorías) — conexión directa con la taxonomía
  de fricciones SOFIA.

## 4. Limitaciones conocidas (declaradas, no ocultas)
- Kaggle bloquea el acceso automatizado: el paso 1 es insustituiblemente
  humano. Sin zip, la skill opera con la suite semilla declarada
  (`hfe_floor_seed.jsonl`, 8 prompts sintéticos/de ejemplo) — válida para
  verificar el motor, NO como evidencia de suelo de ningún modelo.
- La partición pública es 20% estratificado del HFE completo (112/544
  prompts, 28/136 familias): inferencia conservadora, no certificación
  completa.
- HOOTL simula el comportamiento del modelo, no los datos: prompts y
  respuestas de referencia son los reales de HFE una vez ingeridos.

## 5. Glosa compacta (PROP-GLOSA-AMPLIT-001, 10 campos)
1. **Descripción**: skill de ingesta+evaluación de fiabilidad de suelo HFE.
2. **Origen**: AVFrere-c (Vibe/GLM-5.3), 26/11/2026, sesión S-20261126-VIB; padre llm-as-a-verifier#3.
3. **Motivos**: integrar la metodología HFE como capa de evaluación de suelo de MacQAS (recomendación AVFrere-b).
4. **Consecuencias**: umbral canónico computable antes de promover modelos entre entornos; métrica familiar estricta disponible por subcategoría.
5. **Recomendación**: adoptar tras validar con el dataset real (confianza alta en el motor, media en la suite hasta ingerir los 112 prompts).
6. **Opciones**: evaluadas — espejo HF/GitHub (inexistente, verificado 26/11), descarga automatizada (bloqueada), suite semilla (adoptada como fallback).
7. **Reversibilidad**: Sí — retirar la skill no altera los datos ni otros componentes del stack.
8. **Riesgo**: HOOTL en pasos 3-5; HOTL en el 2; HITL en el 1. Perímetros no delegables: sin credenciales en el pipeline (SP-04), sin borrados.
9. **Relevancia**: 4/5 — habilita la métrica de suelo para el Router Sofia y el Banco de Skills; vigente.
10. **Referencias**: PR #3 de llm-as-a-verifier; docs/INGESTA_HFE_PUBLIC.md; docs/HFE_TAXONOMIA.md; informe técnico HFE (storage.googleapis.com/deepmind-media/papers/hfe_tech_paper.pdf).

## Bloque de Procedencia (DEC-TRAZ-REG-001)
Origen registro: AVFrere (Vibe/Mistral, GLM-5.3) · Fecha-hora registro:
2026-11-26 · Propósito: dar de alta la skill del pipeline Suelo HFE en el
Banco del harness por orden de AVF ("desarrolla una skill script") · Clave:
S-20261126-VIB · Padre: PR #3 llm-as-a-verifier.
