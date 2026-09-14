# ADR-DOC-WORKFLOW-001: Adopción del Workflow doc-analysis-wf como Estándar AVF

- **Estado:** Proposed (Candidate — pendiente aprobación HITL)
- **Fecha:** 2026-09-14
- **Decisor:** Alberto Vila Ferrer (AVF)
- **Consultor:** AVFrere — Copiloto de Dirección Estratégica
- **Repo origen:** `skills/doc-analysis-wf` (sistema de habilidades Vibe)

## Contexto

El análisis del artículo AtomRAG (Igolnikov & Abbas, 2026) demostró la
necesidad de un workflow reproducible para análisis documental orientado a
SOFIA Human-AI. El workflow manual aplicado (OCR → síntesis → investigación →
análisis estratégico → stress-test → revisión → gobernanza → Canvas → registro)
produjo un informe de calidad en ~90 min, pero no era reusable.

## Decisión

Adoptar **doc-analysis-wf** como skill Vibe estándar para análisis de
documentos, artículos y noticias. La skill orquesta 10 fases con gates W0–W6,
alineadas a protEARS, KBD Human-AI y gobernanza AI Act/GDPR.

## Validación

3 tests ejecutados sobre tareas pendientes de MEM-KORE:

| Test | Artículo | Tarea pendiente | Veredicto |
|---|---|---|---|
| 1 | Trustworthy Agentic AI (Qi et al., 2026) | G2 SOFIA-RECUPERA | ✅ Aprobado |
| 2 | Meta-reasoning (Talukdar et al., 2026) | REM-05 Silo Perplexity | ✅ Aprobado |
| 3 | Multi-agent Geosimulation (Padilla & Dávila, 2026) | HITL-02 ADRs GitHub | ✅ Aprobado |

Los 3 tests validan v1.1 como la primera versión production-ready.

## Consecuencias

- **Positivas**: workflow reproducible, auditable, con gobernanza HitL/HotL/HooTL.
- **Negativas**: overhead de 10 fases puede ser excesivo para documentos cortos.
- **Mitigación**: CaseEnvelope ajusta presupuesto (EUR, min, retries) por documento.

## Compliance

- **AI Act**: gates de supervisión humana (HitL), trazabilidad (logging MEM-KORE),
  transparencia (notas a pie de página con citas).
- **GDPR**: regla no_pii, minimización de datos.
- **Green AI**: presupuesto de tokens/EUR, motor frugal H-2.

## Relaciones

- Implementa DEC-062 (kernel P0 con policy y tests).
- Avanza SOFIA-RECUPERA G2 (mapeo assurance hooks → gates).
- Resuelve HITL-02 (plantilla ARM para 11 ADRs).
- Avanza REM-05 (meta-reasoning para poblar Silo Perplexity).

## Próximos pasos

1. Aprobación HITL de Alberto Vila Ferrer (gate protRevDial).
2. Procesar los 10 artículos restantes con doc-analysis-wf v1.1.
3. Registrar resultados en MEM-KORE, Drive y GitHub.

---

*Generado por AVFrere bajo workflow Mistral Vibe. Principio rector SOFIA:
«La IA amplifica el criterio humano; no lo sustituye.»*
