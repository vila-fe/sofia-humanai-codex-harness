# ADR-SO-SR-001 — Protocolo agnóstico de investigación sistemática SO-SR v0.2

- **Estado:** Approved (HITL AVF, 25/09/2026)
- **Fecha:** 2026-09-25
- **Autor:** AVFrere (Vibe, Mistral) · AVF Strategic Consulting
- **Decisión relacionada:** DEC-KBD-001 (KBD federadas), EP-2026-09-25-A

## Contexto

El Programa SOFIA necesita un proceso reproducible y skillizable de investigación
sistemática documental (interna/externa) reutilizable en cualquier LLM o herramienta,
incluidos proyectos de cliente (CATA).

## Decisión

Adoptar SO-SR v0.2 como protocolo agnóstico con formato `sofia.protocol/v1`:

1. **Cuerpo agnóstico** (fases R0-R6 + gates G0-G4): ejecutable por cualquier LLM.
2. **Registro de adaptadores** (`adapters.yaml`, patrón REGAL): capacidades separadas
   de herramientas; cambiar stack = editar YAML.
3. **Paquete de exportación**: protocolo + adapters.yaml + gobernanza (CaseEnvelope,
   HitL/HotL/HooTL, PRISMA-trAIce).

### Matriz de orquestación (criterio)

- Flujos mecánicos HooTL → Zapier (primario) o Make (coste).
- Datos personales/cliente → n8n self-hosted (soberanía, AI Act/GDPR).
- Portabilidad de capa LLM → OpenRouter (API unificada, fallback automático).
- Gates programados → Cloudflare Workers.

## Consecuencias

- (+) Portabilidad total entre sesiones/herramientas; reutilización comercial (CATA).
- (+) Trazabilidad AI Act: divulgación PRISMA-trAIce por etapa.
- (-) Coste de mantener adapters.yaml actualizado por stack.
- (-) Riesgo de deriva entre copias — el GitHub es la fuente de verdad del protocolo.

## Validación (HITL)

- 25/09/2026: Aprobado por AVF en sesión Vibe (HITL). Condición: 2 pilotos
  (1 rápido, 1 estándar) antes de promocionar a skill Vibe definitiva.

## Próximos pasos

1. 2 pilotos de validación (1 rápido, 1 estándar).
2. Replicar el patrón para SO-WF y SO-KM (mismo formato v1).
3. Verificación inter-juez trimestral de umbrales de gates.
