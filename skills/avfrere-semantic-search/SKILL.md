---
name: avfrere-semantic-search
description: >-
  Capa transversal de búsqueda y análisis semántico sobre MEM-KORE, Cluster de
  Memorias/KDB, Unidad Cognitiva y memorias AVFrere (atajo /semanticSearch):
  federación de consulta con procedencia, reranking y síntesis con evidencia.
  Usar ante "busca en memoria", "recupera contexto", "qué sabemos de X".
---

# avfrere-semantic-search — Búsqueda semántica federada SOFIA (homologado v1.0)

Homologación portable de `Skill_SemanticSearch_AVFrere_MEM-KORE` (Notion) e
integrada como capa transversal del arranque `AVFrere,` (§17 del skill maestro).
Fuente canónica: la página Notion vigente prevalece.

## 1. Propósito
Actuar como capa general de recuperación sobre MEM-KORE, Cluster de Memorias/KDB,
Unidad Cognitiva, Memoria Intersesiones y memorias de Gemelos SOFIA. **No crea una
memoria nueva ni fusiona físicamente repositorios**: federa la consulta y conserva
procedencia, estado, versión, temporalidad y autoridad de cada fuente.

## 2. Atajo canónico
`/semanticSearch`

## 3. Procedimiento
1. Normalizar la intención de la consulta.
2. Extraer conceptos, entidades, relaciones, proyecto, protocolo, actor, estado y
   horizonte temporal.
3. Si la búsqueda semántica nativa de Notion está disponible, usarla como primera
   vía; si no, fallback híbrido léxico + análisis semántico (PROC-012: TF-IDF +
   embedding + reranking).
4. Buscar candidatos en MEM-KORE, Cluster/KDB, Unidad Cognitiva, Memoria
   Intersesiones, memorias AVFrere y Gemelos, respetando permisos y fuentes
   realmente conectadas.
5. Recuperar contenido relevante y reranquear por pertinencia semántica, recencia,
   autoridad y evidencia.
6. Detectar duplicados, contradicciones, obsolescencia, dependencias y relaciones
   entre memorias.
7. Clasificar cada hallazgo: `CANÓNICO / ACTIVO / HISTÓRICO / PROPUESTA /
   CANDIDATO / OBSOLETO / CONFLICTO / EVIDENCIA`.
8. Separar siempre **hechos, inferencias, hipótesis y decisiones pendientes**.
9. Entregar síntesis con mapa de evidencia y procedencia. Una coincidencia
   semántica no se convierte automáticamente en verdad ni una propuesta en
   ejecución.

## 4. Arquitectura lógica
`Consulta` → `/semanticSearch` → MEM-KORE → Cluster Memorias/KDB → Unidad
Cognitiva → Memoria Intersesiones → AVFrere/Gemelos SOFIA → Ranking + Evidence →
Síntesis → Decisión/Acción.

## 5. Reglas de seguridad
- No recuperar ni exponer secretos, tokens ni credenciales.
- No escribir memoria canónica automáticamente.
- Cambios estructurales o persistentes requieren el gate correspondiente.
- En conflicto entre fuentes, prevalece la fuente canónica vigente y la decisión
  HITL superior.

## 6. KPIs
- Recall percibido sobre consultas de prueba (objetivo ≥63% W-INVESTIGA v2).
- % de hallazgos con procedencia completa (fuente, fecha, estado).
- Duplicados y contradicciones detectados por sesión.
