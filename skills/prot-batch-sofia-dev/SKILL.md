---
name: prot-batch-sofia-dev
description: >-
  Regla escrita y repetible de cómo operar la cola de desarrollo de código SOFIA
  bajo ProtAutom/HOOTL: clasificación automática de pendientes sin preguntar
  primero, verificación anti-staleness por sesión y registro proactivo.
---

# prot-batch-sofia-dev — Operación HOOTL del desarrollo de código SOFIA (homologado v1.0)

Homologación portable de `SKILL_protBatchSofiaDev_v1` (Notion, 30/08/2026, piloto).
Fuente canónica: la página Notion vigente prevalece.

## 0. Relación con protocolos existentes (no sustituye, integra)
Aplica en el dominio de desarrollo de código SOFIA: ProtAutom (5 fases: Explicación
→ Autorización → Ejecución → Reporte → Validación), PROC-010 (aprobada ≠ ejecutada
sin evidencia), PROC-011 v1.1 (~50 chars por código citado), PROC-003 v1.1 (~200
chars por episodio: problemática/relevancia/solución), ADR-0006 (umbrales ≥0.92
autónomo, 0.70-0.92 escalada SOFT, <0.70 escalada HARD).

## 1. Regla de clasificación y ejecución automática (HOOTL)
Ante cualquier pendiente de Decisiones SOFIA que toque desarrollo de código,
clasificar **sin preguntar primero**:

| Caso | Acción autónoma (HOOTL) |
|---|---|
| Tipo = HOOTL | Ejecutar directamente, registrar Resultado real, informar después |
| HITL con autorización autosuficiente | Ejecutar en cuanto AVF autorice; con autorización genérica ("ejecuta el grupo X"), solo ítems autocontenidos |
| HITL con dato/decisión sustantiva ausente | NO fabricar la sustancia; listar qué dato falta y esperar |
| Bloqueado por conector inactivo | Reverificar el estado vivo en cada sesión; si sigue inactivo, declararlo, nunca improvisar workarounds |
| Tipo = Manual (solo AVF) | Detallar la acción exacta y por qué no es delegable; revisar si sigue siendo cierto |
| Trigger de escalada AGENTS.md (p.ej. añadir/cambiar proveedor LLM) | Nunca autoejecutar; el trigger prevalece sobre cualquier clasificación |

## 2. Verificación anti-staleness por sesión (confirmado AVF 07/09)
Si pasaron varios días desde la última verificación en vivo, reconsultar Decisiones
SOFIA antes de actuar sobre cualquier grupo (P0/P1/P2) mencionado en una sesión
anterior. Motivo verificado: entre 31/08 y 07/09 las 4 filas P0 se resolvieron en
sesiones intermedias sin que ninguna sesión posterior lo supiera hasta reconsultar.

## 3. Regla de registro proactivo (instrucción AVF 10/09)
Cualquier propuesta/protocolo/herramienta del stack que no esté en Decisiones SOFIA
se registra directamente como fila nueva (Pendiente AVF o En Reserva según
corresponda) — sin preguntar primero. Registrar es de bajo riesgo; preguntar antes
es la fricciún a eliminar. Sigue vigente: no fabricar la sustancia de la decisión
de AVF.

## 4. Aplicación a frentes específicos
- **Router Sofia + EARS:** verificar CI y estado de merge antes de tocar.
- **Copiloto AVFrere:** el piloto de validación (medir N interacciones) puede
  ejecutarse en chat sin depender de conectores.
- **MacQAS-VM:** experimental por diseño; no autoejecutar despliegues reales.
- **WIKI/GraphRAG/CompactifAI:** no diseñar integraciones sin leer la spec real primero.

## 5. Condiciones de éxito/fallo del piloto
**Éxito:** en 2-3 sesiones futuras, el agente clasifica y ejecuta sin que AVF
repite las reglas, y ninguna acción irreversible se ejecuta sin la autorización
que le correspondía.
**Fallo:** el agente fabrica una decisión sustantiva de AVF, ejecuta algo
bloqueado por conector asumiendo disponibilidad, o deja de reverificar el estado
real antes de actuar.
