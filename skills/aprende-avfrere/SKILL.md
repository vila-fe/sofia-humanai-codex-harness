---
name: aprende-avfrere
description: >-
  Calibración de juicio de AVFrere contra AVF usando desacuerdos como señal
  (disparador "Aprende, AVFrere."): registra recomendación previa + coincidencia
  y busca patrones de divergencia. Distinta de "aprende:" (tutoría AVF).
---

# aprende-avfrere — Calibración de juicio vs. AVF (homologado v1.0 + anexo v1.1)

Homologación portable de `SKILL_aprende-AVFrere_v1` (Notion, 22/07/2026) y su
anexo v1.1 "Memoria-como-herramienta + Guías destiladas" (25/09/2026, PROP-APRENDE-002).
Fuente canónica: la página Notion vigente prevalece.

## 1. Propósito
Distinta de `aprende:` (tutoría socrática para que AVF aprenda). Esta skill es para
que **AVFrere** aprenda de **AVF**: calibrar dónde el juicio del agente se desvía
sistemáticamente del de Albert, usando los **desacuerdos** como señal principal,
no los acuerdos.

## 2. Mecánica
Cada vez que el agente dé una recomendación explícita sobre una decisión de
gobernanza/diseño y AVF resuelva, se registra el par en Decisiones SOFIA con:
- **Recomendación del agente** (texto libre), registrada *antes* de conocer la
  decisión final de AVF cuando sea posible (evita sesgo retrospectivo).
- **Coincide con AVF** (Sí / No / Parcial / N-A): comparación tras el hecho.

## 3. Disparador de registro
Se registra en ambos casos, para no perder señal:
- Cuando AVF señala explícitamente desacuerdo con la recomendación.
- Cuando el agente detecta, al revisar la decisión final, que difiere de lo que
  propuso — lo señala él mismo, sin esperar a que AVF lo note.

Frase disparadora: "Aprende, AVFrere." al inicio de mensaje.

## 4. Uso del historial
Periódicamente o bajo demanda (`aprende: mis desacuerdos con AVF`), consultar el
historial de coincidencias = No/Parcial para buscar patrones. El objetivo no es
imitar a AVF sin criterio propio, sino entender **dónde y por qué** diverge.

## 5. Salvaguarda anti-sesgo retrospectivo
La recomendación se registra antes de conocer la decisión de AVF; si se registra
a posteriori, se marca explícitamente como reconstrucción, no como predicción.

## 6. Anexo v1.1 — Memoria-como-herramienta (25/09/2026)
La memoria episódica debe poder invocarse como herramienta consultable en el
momento de decidir (no solo como lectura de arranque). Incluye 8 guías destiladas
de desacuerdos históricos. Estado: Candidate; si los gates G-05/G-06 pasan al
Reglamento SOFIA, se promueve (pendiente HOTL de AVF).

## 7. Estado
🟡 Piloto — acumulando casos reales de desacuerdo para evaluar si el patrón
emergente es útil o ruido.
