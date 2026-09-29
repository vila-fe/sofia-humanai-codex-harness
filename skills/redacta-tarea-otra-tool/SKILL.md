---
name: redacta-tarea-otra-tool
description: >-
  Protocolo skillizable de redacción de paquetes de tarea autocontenidos destinados
  a ser ejecutados por otra herramienta/plataforma (la que dispone del conector
  requerido). Disparador: "Redacta para otra Tool".
---

# redacta-tarea-otra-tool — Paquetes de tarea para otra herramienta (v1.0)

Protocolo skillizable. Disparador: **"Redacta para otra Tool"**.

Fuente canónica: la página Notion vigente prevalece.

## 1. Propósito

Cuando una tarea del programa requiere un conector o capacidad que la sesión
actual no tiene, redactar un paquete de tarea **autocontenido** para que lo
ejecute la herramienta/plataforma que sí dispone de ese conector. La redacción
no menciona el caso concreto: el protocolo queda abierto al nuevo caso que lo
dispare.

## 2. Contenido obligatorio del paquete

Todo paquete redactado bajo este protocolo incluye, en este orden:

1. **Contexto**: qué sistema/proyecto afecta, estado verificado y por qué la
   herramienta destinataria es la correcta (conector que posee).
2. **Objetivo**: resultado verificable esperado, sin ambigüedad.
3. **Pasos exactos**: secuencia accionable y reproducible; incluir comandos,
   rutas o consultas cuando existan.
4. **Criterios de aceptación**: condiciones objetivas que determinan que la
   tarea está completa.
5. **Evidencia a registrar**: qué debe capturar y guardar la herramienta
   ejecutora (IDs, capturas, logs, enlaces) conforme a PROC-010
   (aprobada ≠ ejecutada sin evidencia).
6. **Reglas**: no fabricar datos ausentes; preservar los gates HITL/HOTL del
   ámbito afectado; describir cada código/artefacto citado (~50 chars,
   PROC-011 v1.1); resumir el episodio en ~200 chars
   (problemática/relevancia/solución, PROC-003 v1.1).

## 3. Regla de cierre y traspaso

Una vez redactado el paquete, y tras la revisión y validación del responsable
humano (HITL), guardar con el cierre de sesión registrándolo como **tarea
prioritaria para la herramienta que tenga el conector** al sistema afectado,
identificando explícitamente la herramienta destinataria y el sistema objetivo.

## 4. Validación

El paquete redactado se somete siempre a validación humana antes del traspaso.
Si falta un dato sustantivo, se lista lo que falta y se espera; nunca se
improvisa ni se rellena con suposiciones.
