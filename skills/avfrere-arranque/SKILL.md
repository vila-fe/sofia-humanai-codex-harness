---
name: avfrere-arranque
description: >-
  Skill maestro secuencial de arranque intersesional SOFIA (disparador "AVFrere,"):
  lee Reglamento SOFIA + Tablero de Arranque, recupera MEM-KORE de Notion, último
  episodio y decisiones pendientes, aplica /protRevDial + /protAutom2 y batch EARS
  con gates HOOTL/HITL.
---

# avfrere-arranque — Arranque intersesional AVFrere (homologado v1.0)

Homologación portable de `Skill_AVFrere_arranque` (Notion, MEM-KORE, ed. 19/09/2026)
al Banco de Skills del harness. Fuente canónica: la página Notion vigente prevalece.

## 1. Propósito
Orquestar en una única skill el arranque intersesional, revisión crítica, ejecución
HOOTL y batch secuencial verificable del Programa SOFIA, integrando
`protArranque-SOFIA`, `/protRevDial`, `/protAutom2` y `SKILL_protBatchSofiaDev_v1`.

## 2. Disparador y arranque
Cuando el primer mensaje de una nueva sesión comienza con `AVFrere,`:
1. Leer primero el Reglamento SOFIA (índice de convenciones canónicas) y después el
   Tablero de Arranque.
2. Consultar MEM-KORE en Notion.
3. Recuperar el último Episodio SOFIA y las Decisiones SOFIA pendientes.
4. Incorporar cualquier cierre de sesión aportado por AVF.
5. Confirmar exactamente: "Memoria intersesión incorporada."
6. No repetir la recuperación ante menciones posteriores en la misma sesión.
7. En sesión nueva, re-verificar memoria y estado vivo; no asumir que una cola
   antigua sigue vigente (regla anti-staleness).

## 3. Gate de revisión crítica (/protRevDial)
Antes de acciones de impacto relevante: delimitar objeto y contexto; detectar
supuestos, lagunas y restricciones; identificar tesis, antítesis y contradicción
operativa; contrastar con el marco SOFIA y recursos reales; formular síntesis
dialéctica. Emitir: **Válido / Válido con condiciones / Prematuro / No recomendable
por ahora**. "No recomendable" detiene la cadena; "Prematuro" identifica lo que
falta y no ejecuta; "Válido con condiciones" transporta las condiciones al
siguiente gate.

## 4. /protAutom2: ejecución por ciclo verificable
1. Definir objetivo, entregable y evidencia observable.
2. Desglosar acciones: qué, cómo, dónde, quién, cuándo, por qué.
3. Identificar consecuencias, dependencias y riesgos.
4. Ejecutar solo lo autorizado y dentro del alcance.
5. Registrar evidencia real, resultados, fallos, costes y decisiones.
6. Reportar el bloque: logrado/no logrado, evidencia, desviaciones, riesgos,
   siguiente gate.
7. Esperar validación humana cuando corresponda: VALIDADO / RECTIFICAR /
   MODIFICAR / STOP.

## 5. Clasificación HOOTL/HITL
- **HOOTL:** ejecutar directamente, registrar Resultado real e informar después.
- **HITL con autorización autosuficiente:** ejecutar ítems autocontenidos autorizados.
- **HITL con dato/decisión sustantiva ausente:** no fabricar la decisión; listar el
  dato faltante y esperar.
- **Manual:** detallar exactamente qué debe hacer AVF y por qué no es delegable.
- **Trigger de escalada (AGENTS.md):** prevalece sobre cualquier clasificación; no
  se autoejecuta.
- **Conector inactivo:** reverificar su estado vivo; si sigue inactivo, declararlo y
  no improvisar workarounds.

## 6. Batch secuencial EARS
Descomponer el objetivo en B[n] con dependencia explícita. Por bloque: entrada,
transformación, salida, responsable, KPIs, riesgos, presupuesto, permisos, prueba y
gate HOOTL. **B[n+1] no puede comenzar hasta que B[n] esté validado.** Por bloque:
ejecutar en sandbox; validar contra criterios de aceptación; registrar fuentes,
versiones, resultados y aprendizaje en MEM-KORE; pasar gate (aprobar / corregir /
reducir alcance / repetir / detener); solo tras aprobación promover la salida como
entrada de B[n+1].

## 7. Gates obligatorios
Datos (fuentes nuevas/sensibles) · Modelo (simulación como recomendación) ·
Agente (herramientas/permisos nuevos) · Seguridad (preprod/prod) · Acción (cambios
externos o irreversibles). Cualquier STOP prevalece sobre la continuidad automática.

## 8. Reglas de integración (SKILL_protBatchSofiaDev_v1)
- Reconsultar en vivo Decisiones SOFIA si pasaron varios días desde la última
  verificación.
- No tratar una fila `Aprobada` como ejecutada sin evidencia real en `Resultado`
  (PROC-010).
- Descripciones breves del código citado y resúmenes episódicos conforme a
  PROC-011 (~50 chars por código) y PROC-003 v1.1 (~200 chars: problemática /
  relevancia / solución).
- Respetar umbrales de confianza y escalado de ADR-0006 cuando aplique.
- No diseñar integraciones cuya especificación real no se haya leído.

## 9. Plantilla mínima B[n]
```yaml
block_id: B[n]
objective: ""
inputs: []
allowed_tools: []
forbidden_actions: []
outputs: []
acceptance_criteria: []
risks: []
budget: {time: "", cost: "", tool_calls: 0}
gate: "HOOTL approval required"
status: pending
```

## 10. Regla maestra de seguridad
No simular ejecuciones. Diferenciar siempre ejecución real, borrador, hipótesis y
recomendación. No superar permisos, alcance, presupuesto ni autonomía autorizados.
Ante error crítico o dos fallos equivalentes: detener, preservar evidencia y
escalar con alternativas.

## 11. Cadena canónica
`AVFrere,` → protArranque-SOFIA → MEM-KORE vivo → /protRevDial → /protAutom2 →
clasificación HOOTL/HITL → Batch EARS → gates por bloque → validación → MEM-KORE →
B[n+1].

## 12. Principio de despliegue gradual
Ampliar alcance solo cuando el bloque anterior demostró valor, seguridad y
evidencia suficiente. Sandbox/local primero, mínimo privilegio, reversibilidad,
bajo coste. La evidencia gobierna la secuencia, no el calendario.

## 13. Precedencia
Este skill integra y no sustituye los protocolos originales. Ante conflicto,
consultar la página canónica Notion más reciente del protocolo específico y
respetar gates superiores, decisiones HITL y restricciones de seguridad.
