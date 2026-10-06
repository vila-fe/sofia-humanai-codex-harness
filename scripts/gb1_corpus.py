#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GB-1 corpus: materialización de los chunks canónicos del Carril A (SPEC-GRAPHRAG-001).

Procedencia: Sesión S-20261006-VIB · Padre EP-2026-10-06-U (hallazgo: corpus no materializado) ·
Gate GB-1 (hit-rate@5 >= 70%) · Presupuesto 0 EUR (stdlib pura, patrón sofia-python-scripts v0.1).

Funciones:
  - gen    : escribe el corpus de chunks canónicos en JSON compatible con gb1_embeddings.py --manifest.
  - verify : gate PASS/FAIL — todos los expected_chunk_ids del golden set existen y sin duplicados.

Los textos son extractos canónicos verbatim de las fuentes del Programa (Reglamento SOFIA,
MEM-KORE §7, decisiones y specs), sin secretos ni datos personales, citando fuente en cada chunk.

Uso:
  python scripts/gb1_corpus.py gen    [--out docs/index/carril-a/corpus-carril-a-v0.1.json]
  python scripts/gb1_corpus.py verify [--corpus docs/index/carril-a/corpus-carril-a-v0.1.json]
                                      [--golden docs/index/carril-a/golden_set_v0.1.json]

Tras gen, el run completo del gate GB-1 es:
  python scripts/gb1_corpus.py gen
  python scripts/gb1_embeddings.py index --manifest docs/index/carril-a/corpus-carril-a-v0.1.json
  python scripts/gb1_embeddings.py eval  --golden docs/index/carril-a/golden_set_v0.1.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_OUT = "docs/index/carril-a/corpus-carril-a-v0.1.json"
DEFAULT_GOLDEN = "docs/index/carril-a/golden_set_v0.1.json"
SPEC = "SPEC-GRAPHRAG-001"
VERSION = "v0.1"

CHUNKS = {
    "carril-a-marco-sofia-def": (
        "Marco SOFIA Human-AI AVF: gemelo digital de Alberto Vila Ferrer (AVF, AVF Strategic Consulting) "
        "que opera como Anton Vidal Frugal (AVFrere). Rol: asistente estratégico en análisis, síntesis y "
        "diseño de soluciones; coordinador de tareas complejas (cadena de pensamiento, agentes modulares); "
        "validador de hipótesis bajo el marco SOFIA; respetador absoluto de la supervisión HITL de AVF en "
        "decisiones críticas. Restricciones: no tomar decisiones estratégicas sin validación explícita de "
        "AVF; mantener trazabilidad citando fuentes y registrando la cadena de pensamiento; respetar las "
        "políticas de IP (CC-BY-SA para el marco base; licencia comercial para CATA). Límites "
        "computacionales declarados: PC de 8-16 GB RAM, ~40 h/semana disponibles; evaluar siempre las "
        "capas de menor coste antes de escalar a nube. [Fuente: Reglamento SOFIA / marco base]"
    ),
    "carril-a-marco-sofia-principios": (
        "Marco SOFIA — cuatro principios operativos (S-I-F-A). 1) SISTÉMICO: cada análisis debe considerar "
        "dependencias y efectos en el conjunto del proyecto Sofia. 2) INNOVACIÓN ABIERTA: reutilizar "
        "recursos existentes; no reinventar. 3) FRUGAL: mínimo viable en tokens, tiempo de respuesta y "
        "cómputo; el coste marginal 0 va antes que la infraestructura nueva. 4) ADAPTATIVA: las soluciones "
        "deben escalar sin rediseño fundamental. Los cuatro principios se refuerzan simultáneamente como "
        "capa transversal del programa: la frugalidad es credencial competitiva, no handicap (PAT-001), y "
        "el mal ROI de la IA en empresa se debe a gobernanza ausente, no a límites técnicos (PAT-002). "
        "[Fuente: Reglamento SOFIA principios; MEM-KORE §2 PAT-001/002]"
    ),
    "carril-a-hitl-def": (
        "HITL (Human-In-The-Loop): nivel de supervisión en el que ninguna decisión crítica se toma sin "
        "validación explícita del humano (AVF). Ámbito: decisiones estratégicas, cambios de dirección, "
        "escrituras en fuentes de verdad, borrados, política, publicaciones, CATA, credenciales y pagos. "
        "Ante un gate HITL el agente prepara el paquete de decisión (contexto, alternativas, coste, "
        "recomendación) y espera el sí explícito de AVF antes de ejecutar; la aprobación queda registrada "
        "en Decisiones SOFIA con Bloque de Procedencia. La aprobación HITL habilita la ejecución pero no "
        "la sustituye: tras el sí, se verifica en la fuente real que la tarea se ejecutó (PROC-010, "
        "aprobado no significa ejecutado). [Fuente: Reglamento SOFIA gobernanza; marco KBD Human-AI]"
    ),
    "carril-a-supervision-niveles": (
        "Niveles de supervisión del Stack SOFIA. HITL (Human-In-The-Loop): decisión crítica, requiere "
        "aprobación explícita previa de AVF (borrados, política, escrituras en fuente de verdad, pagos, "
        "credenciales). HOTL (Human-On-The-Loop): revisión previa de acciones con efecto externo. HOOTL "
        "(Human-OutOf-The-Loop): automatizaciones maduras, auditadas y de bajo riesgo; el agente actúa "
        "sin confirmación previa y reporta al final. Regla AVF del 24/09/2026: en casos no críticos "
        "—reversibles, sin contraseñas, sin órdenes de pago— AVF prefiere modalidad HOOTL: actuar sin "
        "pedir confirmación y reportar al cierre; HITL se reserva para lo crítico. Verificar siempre en "
        "la fuente real antes que fiarse del registro narrativo (DEC-071). [Fuente: regla permanente AVF "
        "24/09; PROP-SUPERV-001]"
    ),
    "carril-a-proc010": (
        "PROC-010 — Verificación Sistémica de Trazabilidad (aprobado ≠ ejecutado). Principio rector: una "
        "decisión Aprobada es una promesa, no un hecho, hasta que exista evidencia verificable de "
        "ejecución (campo Resultado no vacío y sin lenguaje de pendiente/bloqueado). Procedimiento: "
        "consulta SQL sobre Decisiones SOFIA con Estado='Aprobada' AND Resultado IS NULL; comprobación "
        "de ventanas temporales vencidas; revisión de reservas con condición cumplida; verificación "
        "cruzada contra el sistema real de cada capa (Supabase, GitHub, Drive, HuggingFace en vivo; "
        "Obsidian solo verificable por AVF); clasificar hallazgos y registrar los estancados como "
        "propuestas nuevas; nunca marcar nada como ejecutado durante la detección. Disparadores: cierre "
        "de sesión con ≥3 decisiones nuevas, ciclo semanal (últimas 1-2 semanas), ciclo mensual (barrido "
        "completo desde el origen) y demanda explícita de AVF. Métrica de salud: aprobadas sin Resultado "
        "con antigüedad >2 semanas, tendencia decreciente. [Fuente: MEM-KORE §7 PROC-010]"
    ),
    "carril-a-procedencia-bloque": (
        "Bloque de Procedencia (DEC-TRAZ-REG-001): todo registro de Episodios, Decisiones y fichas SACR-A "
        "lleva un bloque estándar de trazabilidad con los campos: Origen registro (agente y LLM, p. ej. "
        "Vibe/Mistral AVFrere); Fecha-hora registro con granularidad de segundos y zona horaria (ISO 8601, "
        "p. ej. 2026-10-06T18:40:00+02:00 Europe/Madrid); Propósito (por qué se registra); Padre "
        "(jerarquía átomo→episodio→decisión); uid corto opcional; y clave de sesión S-YYYYMMDD-HHMMSS-ORIG. "
        "Regla anti-colisión: pre-inserción consultar la BD por prefijo de fecha, post-inserción verificar "
        "unicidad del código; los códigos son inmutables salvo que tengan cero referencias entrantes; la "
        "verificación anti-colisión se ejecuta en el instante de la inserción, no en el arranque de la "
        "sesión. [Fuente: DEC-TRAZ-REG-001 v1.1; EP-2026-10-06-L]"
    ),
    "carril-a-dec073": (
        "DEC-073 — Ponderación objetiva de pendientes (momento/inercia real). Criterios con pesos: V "
        "valor estratégico (0,40); M momento o inercia real (0,25); D disponibilidad inmediata, menos "
        "actores externos (0,35); S señalización por cierre o proceso (0,5); C coste en tiempo/dinero "
        "(0,45); E energía de arranque (0,35); R riesgo (0,20). Fórmula ISP v1 (script isp_v1.py en "
        "sofia-twin-digital-avf): (0,40·V + 0,25·M + 0,35·D + 0,5·S) / (0,45·C + 0,35·E + 0,20·R), cada "
        "variable en escala 0-10. Sin datos para un criterio se marca ND y se usa el valor neutro, nunca "
        "se inventa. La ponderación es informativa para AVF: orienta, no sustituye su criterio. Sirve "
        "para jerarquizar la cola de pendientes y separar el Top-3 de acción inmediata de los quick wins "
        "agrupables en un lote. [Fuente: DEC-073; skill sofia-verifica-pendientes v0.2]"
    ),
    "carril-a-router-sofia": (
        "Router Sofia — capa de decisión y conectividad LLM del Stack SOFIA. Implementación real (no mock) "
        "en sofia-twin-digital-avf con 4 proveedores (anthropic/deepseek/mistral/perplexity), homologación "
        "en curso G-Jev F0-F4. PROP-JEV-CASCADA-001 (aprobada): cascada híbrida de capa LLM — Router Sofia "
        "local (capa 1, frugal) → OpenRouter (capa 2, fallback y portabilidad) → RouteLLM/LiteLLM (solo si "
        ">50k tokens/día recurrentes). Evidencia 28/09: cascada Jev→Opus 0,69 USD/1.000 vs 2,42 USD/1.000, "
        "84,0% vs 84,4% acierto. DEC-ANYJEV-001: AnyJev (Nokia, open-source) candidato de capa 1. DeepSeek "
        "V4.1 Flash homologación H-2 como motor frugal candidato de SOFIA-RECUPERA. Trazabilidad del Router: "
        "registro de discrepancias router vs AVF durante el piloto. [Fuente: PROP-JEV-CASCADA-001; "
        "DEC-ANYJEV-001; Knowledge sofia-human-ai]"
    ),
    "carril-a-radar-sofia": (
        "Radar Sofia — ciclo de vigilancia estratégica del Programa SOFIA (Radar→Conocimiento→Unidad "
        "Cognitiva). Capa semanal (DEC-076): tirada automática (tarea programada) + revisión de fichas por "
        "AVF; W40 y W41 ejecutadas; queries Radar v2 con fuentes ampliadas, gate ≥1 hallazgo, máx. 2 "
        "fichas por query y 1 retry. Capa diaria (SP-RD1, PROP-RADAR-DIARIO-001): kit v0.2, tarea diaria "
        "08:20 Europe/Madrid, captura y prefiltro determinista TDS, fichas RD-D-* en SACR-A, episodio solo "
        "si hay hallazgo crítico. Fichas de vigilancia con grado SOFIA (p. ej. ALTO-CRÍTICO en Harness/"
        "Graph/Loop Engineering). El Radar alimenta la base Señales SOFIA/SACR-A, no MEM-KORE §6 (vista "
        "histórica congelada). [Fuente: DEC-076; SP-RD1; B4-L4]"
    ),
    "carril-a-dec-mem-atomo-001": (
        "DEC-MEM-ATOMO-001 — chunking híbrido vectorial-grafo para la memoria. Lo generado en cada sesión "
        "se trocea en chunks (recursive 512-1024 sin overlap) con sus claims y aristas de relación; los "
        "chunks alimentan el índice vectorial del Carril A y las claims/aristas el grafo condicionado del "
        "Carril B (SPEC-GRAPHRAG-001: Carril A híbrido BM25+vector+RRF siempre activa; Carril B grafo solo "
        "si el mini-bench ≥50 consultas muestra ≥20% de consultas multi-hop). Los átomos MacQAS (átomo→"
        "episodio→decisión, con vínculos Padre/uid) heredan el ciclo MEM-KORE completo: percibir→indexar→"
        "reflexionar→actualizar→trazar. Context engineering aplicado: la ingesta explícita UC/Wiki forma "
        "parte del acceso al Núcleo Duro. [Fuente: DEC-MEM-ATOMO-001; SPEC-GRAPHRAG-001 v1.0; PROP-HGL-001]"
    ),
    "carril-a-unidad-cognitiva": (
        "Unidad Cognitiva (UC) — arquitectura cognitiva del Programa SOFIA: MEM-KORE (memoria dinámica) + "
        "Wiki SOFIA + KBD federadas (varias bases de conocimiento federadas, no una pieza única — DEC-KBD "
        "24/09) + aristas de relación entre nodos, con la recuperación híbrida del Carril A como acceso. "
        "Regla UC-HGL-R1 (anti-trampa de grafo, aprobada): la UC NO se escala a arquitectura de grafo "
        "multiagente sin evidencia objetiva — mini-bench de ≥50 consultas reales con ≥20% multi-hop; "
        "mientras el umbral no se alcance, la UC opera como loop bien diseñado dentro del harness "
        "existente (MEM-KORE + Carril A + enjambre MacQAS), sin orquestador-worker ni handoffs entre nodos "
        "LLM. Política de compaction v0.1 de la memoria episódica: ventana activa 30 días + síntesis "
        "mensual como índice, sin borrar episodios. [Fuente: DEC-UC-HGL-R1; DEC-KBD; PROP-HGL 04/10]"
    ),
    "carril-a-mem-kore": (
        "MEM-KORE v1.0 — Memoria Dinámica SOFIA (Notion, bajo el Programa SOFIA Human AI AVFEARS). "
        "Secciones: §0 identidad del sistema; §1 contexto activo (cierres de sesión, orden descendente, "
        "el más reciente arriba); §2 patrones consolidados con confianza en estrellas; §3 episodios "
        "recientes (hoy vista histórica congelada; la fuente viva es la base Episodios SOFIA); §4 grafo de "
        "relaciones activas; §5 propuestas pendientes de validación HITL; §6 señales del entorno (las "
        "nuevas van a SACR-A); §7 procedimientos validados (PROC-001...PROC-013); §8 protocolo de "
        "mantenimiento con ciclo semanal (~20 min, lunes) y ciclo mensual (~45 min, primer lunes: grafo, "
        "confianza de patrones, PROC-010 barrido completo, procedimientos, verificación de vistas). "
        "Bases vivas vinculadas: Episodios SOFIA, Decisiones SOFIA, Señales, Patrones, Propuestas. "
        "[Fuente: MEM-KORE v1.0]"
    ),
    "carril-a-protEARS": (
        "ProtEARS — protocolo de cierre canónico del programa (Cierre3/ProtEARS pasa a CANONICAL el "
        "02/10/2026 por decisión de AVF; G4 escrituras externas y G5 promoción canónica autorizadas en "
        "acta). El cierre de sesión registra: resumen PROC-003 v1.1 en ~200 caracteres estructurado en "
        "problemática, relevancia y solución; episodio en la base Episodios SOFIA con código "
        "EP-YYYY-MM-DD-X (anti-colisión verificada en el instante de inserción); decisiones HITL en "
        "Decisiones SOFIA antes de cerrar; escrituras de la sesión y no-acciones; pendientes AVF "
        "declarados; y Bloque de Procedencia. Madurez del protocolo evaluada en 3,18/5 (revisión 04/10) "
        "con puntos de mejora hacia v2. Registro ≠ cierre: un registro intermedio no es acta de cierre. "
        "[Fuente: acta G4/G5 02/10; EP-2026-10-04-L]"
    ),
    "carril-a-seguridad-guardarrailes": (
        "Guardarraíles de seguridad del Stack SOFIA (PROP-SP04 ESCUDO-CLAVES, aprobada 04/10): rotación "
        "manual de claves en Google Cloud; limpieza de los 5 .env (~50 variables) y blindaje "
        "MCP/vault/RLS; guía operativa con checklist de 19 pasos (≈3 días, ~368 EUR, sin producción hasta "
        "cerrar). Reglas duras: nunca pegar credenciales reales en el chat (el valor recibido era "
        "plantilla); secretos siempre en variables de entorno del servidor, no en texto plano vía Git "
        "Credential Manager; tokens de mínimo privilegio (hallazgo DEC-042: 403 por token sin permiso de "
        "creación de repos). Remediación previa: URL de webhook expuesta en 3 docs de Drive (1 público), "
        "copias redactadas creadas; Gate P0 Supabase cerrado (RLS 21/21 tablas activo). "
        "[Fuente: PROP-SP04; DEC-042; Gate P0]"
    ),
}


def _as_text(value):
    return value[0] if isinstance(value, tuple) else value


def build_entries():
    entries = []
    for chunk_id, raw in CHUNKS.items():
        text = _as_text(raw)
        entries.append({
            "chunk_id": chunk_id,
            "source_id": "carril-a-canonicos",
            "text": text,
            "n_tokens": len(text.split()),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return entries


def cmd_gen(args):
    entries = build_entries()
    seen = set()
    for e in entries:
        if e["sha256"] in seen:
            sys.exit(f"[FAIL] chunk duplicado por sha256: {e['chunk_id']}")
        seen.add(e["sha256"])
    out = {
        "spec": SPEC,
        "version": VERSION,
        "tipo": "corpus-carril-a-canonicos",
        "procedencia": "S-20261006-VIB | EP-2026-10-06-U | skill sofia-python-scripts v0.1",
        "chunks": entries,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {len(entries)} chunks -> {args.out} | dedupe sha256 OK | determinista (texto fijo)")
    print(f"[HECHO] manifest={args.out} | compatible con gb1_embeddings.py index --manifest {args.out}")


def cmd_verify(args):
    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    ids = {c["chunk_id"] for c in corpus.get("chunks", [])}
    hashes = [c["sha256"] for c in corpus.get("chunks", [])]
    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    expected = {cid for case in golden.get("cases", []) for cid in case.get("expected_chunk_ids", [])}
    missing = sorted(expected - ids)
    dupes = len(hashes) != len(set(hashes))
    print(f"[INFO] chunks corpus={len(ids)} | esperados por golden={len(expected)}")
    if missing:
        print(f"[FAIL] chunk_ids del golden sin materializar: {missing}")
    if dupes:
        print("[FAIL] sha256 duplicados en el corpus")
    gate = not missing and not dupes
    print(f"[HECHO] gate verify => {'PASS' if gate else 'FAIL'}")
    sys.exit(0 if gate else 1)


def main():
    ap = argparse.ArgumentParser(description="GB-1 corpus: chunks canónicos del Carril A")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_g = sub.add_parser("gen"); p_g.add_argument("--out", default=DEFAULT_OUT); p_g.set_defaults(func=cmd_gen)
    p_v = sub.add_parser("verify")
    p_v.add_argument("--corpus", default=DEFAULT_OUT)
    p_v.add_argument("--golden", default=DEFAULT_GOLDEN); p_v.set_defaults(func=cmd_verify)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
