#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sofia_escaneo_seguridad.py — Escaneo mínimo de seguridad del repositorio (v0.1).

Procedencia: Claude (AVFrere) · 2026-10-07 · S-20261007-CLA · camino B aprobado por AVF (07/10/2026).
Origen del código: extraído del auditor `scripts/sofia_revisa_efectividad.py` v0.2 del repositorio privado
`sofia-human-ai-avf` (lógica de seguridad idéntica: constantes y funciones `invisible_chars` y `scan_text`).
Aquí no hay estructura de Biblioteca de Skills, así que solo se escanea el contenido. Si cambia la lógica en
el auditor, hay que copiarla aquí: son dos copias y pueden desincronizarse.

Qué hace: recorre TODOS los ficheros del repositorio (cualquier extensión; se excluye `.git`) y busca:
  FAIL  caracteres invisibles/bidi/selectores de variación/«tag characters» · secretos
        · órdenes de ignorar instrucciones previas u ocultar acciones al usuario
        · fichero demasiado grande para escanear (>20 MB, falla cerrado)
  WARN  posible envío de credenciales a un destino externo · comandos sospechosos
        · cadenas largas tipo base64 · fichero binario (no escaneable como texto)
  INFO  dominios de las URLs
LIMITACIÓN: detecta patrones, no el sentido; no cubre homoglifos. No sustituye la lectura humana.

Stdlib pura. Determinista. Exit 0 = sin FAIL; 1 = hay FAIL.
Uso: python3 -I scripts/sofia_escaneo_seguridad.py [--dir .]
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

SECRET_PATTERNS = {
    "clave tipo sk-": r"\bsk-[A-Za-z0-9]{20,}",
    "token GitHub": r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "clave AWS": r"\bAKIA[0-9A-Z]{16}",
    "asignación de secreto": r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{20,}",
    "Bearer": r"\bBearer\s+[A-Za-z0-9._\-]{20,}",
    # El literal del token no se escribe aquí: se construye en dos mitades para no propagarlo.
    "token de webhook SOFIA": "SOFIA" + "-HITL-" + r"\d{4}",
}
# Escaneo de inyección (v0.2): busca PATRONES, no entiende el sentido. No detecta una instrucción dañina
# redactada con naturalidad; no sustituye la lectura humana de lo que una skill ordena hacer.
INJECTION_FAIL = {
    "orden de ignorar instrucciones previas": r"(?i)(ignora|olvida|descarta)\s+(todas\s+)?(las\s+)?(instrucciones|reglas)\s+(previas|anteriores)"
                                              r"|ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)|disregard\s+(all\s+)?(previous|prior)",
    "ocultar acciones al usuario": r"(?i)no\s+(le\s+)?(avises|informes|digas)\s+(al\s+)?usuario|sin\s+que\s+(lo\s+sepa\s+)?el\s+usuario"
                                   r"|do\s+not\s+(tell|inform|notify)\s+the\s+user|without\s+(telling|informing)\s+the\s+user",
}
INJECTION_WARN = {
    "posible envío de credenciales a un destino externo": r"(?i)\b(env[ií]a|manda|publica|send|post|upload|exfiltrat\w*)\b[^.\n]{0,60}"
                                                          r"\b(token|clave|credencial|secret|password|api[_ -]?key)\b[^.\n]{0,60}(https?://|\w+@\w)",
}
SUSPICIOUS_CMD = (r"(?i)\b(curl|wget)\b[^\n]*\|\s*(ba)?sh|\beval\s*\(|base64\s+(-d|--decode)|\brm\s+-rf\s+[/~]"
                  r"|\bchmod\s+\+x|\bsudo\b|\bnc\s+-[a-z]*e\b|/dev/" r"tcp/")
URL_RE = r"https?://([A-Za-z0-9.-]+)"
BLOB_RE = r"[A-Za-z0-9+/=]{100,}"


# Caracteres «default-ignorable» de Unicode: no se ven, o no cambian el aspecto del texto, pero sí lo que ve una
# expresión regular. No basta con las categorías Cf/Cs/Co/Cc: los selectores de variación son categoría Mn.
IGNORABLE_RANGES = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
                    (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
                    (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
                    (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF))
BOM, ZWJ, VS15, VS16, KEYCAP = 0xFEFF, 0x200D, 0xFE0E, 0xFE0F, 0x20E3
MAX_SCAN_BYTES = 20_000_000


def _emoji_base(cp):
    """Carácter que puede llevar legítimamente un selector de variación o un ZWJ (símbolos y emoji, no letras)."""
    return cp >= 0x1F000 or 0x2190 <= cp <= 0x2BFF or cp in (0x203C, 0x2049, 0x2122, 0x2139, 0x3030, 0x303D, 0x3297, 0x3299)


def invisible_chars(text):
    """Caracteres invisibles o de control: bidi, ancho cero, «tag characters», selectores de variación y demás
    ignorables. Se toleran el BOM inicial, el ZWJ y los selectores de variación SOLO dentro de secuencias de emoji."""
    found, n = [], len(text)
    for i, ch in enumerate(text):
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if not (any(lo <= cp <= hi for lo, hi in IGNORABLE_RANGES) or cat in ("Cf", "Co", "Cs")
                or (cat == "Cc" and ch not in "\n\t\r\f")):
            continue
        prev = ord(text[i - 1]) if i > 0 else None
        if cp == BOM and i == 0:
            continue
        if cp in (VS15, VS16) and prev is not None and (
                _emoji_base(prev) or (chr(prev) in "#*0123456789" and i + 1 < n and ord(text[i + 1]) == KEYCAP)):
            continue
        if cp == ZWJ and prev is not None and (_emoji_base(prev) or prev == VS16):
            continue
        found.append(f"U+{cp:04X}")
    return found


def scan_text(text, own, label):
    """Devuelve (fails, warns, infos) del escaneo de seguridad de un texto. `own`=False para terceros (con LICENSE)."""
    fails, warns, infos = [], [], []
    inv = invisible_chars(text)
    if inv:
        fails.append(f"{label}: caracteres invisibles o de control ({len(inv)}: {', '.join(sorted(set(inv))[:4])})")
    for name, pat in SECRET_PATTERNS.items():
        if re.search(pat, text):
            fails.append(f"{label}: posible secreto — {name}")
    for name, pat in INJECTION_FAIL.items():
        if re.search(pat, text):
            fails.append(f"{label}: posible inyección — {name}")
    for name, pat in INJECTION_WARN.items():
        if re.search(pat, text):
            warns.append(f"{label}: {name} (leer a mano)")
    if re.search(SUSPICIOUS_CMD, text):
        (warns if own else infos).append(f"{label}: comando sospechoso (descarga y ejecución, eval, decodificación base64, borrado recursivo, permisos de ejecución, elevación de privilegios)"
                                         + ("" if own else " — skill de tercero, revisar"))
    if re.search(BLOB_RE, text):
        (warns if own else infos).append(f"{label}: cadena larga tipo base64/hex (≥100 car.)")
    domains = sorted(set(re.findall(URL_RE, text)))
    if domains and own:
        infos.append(f"{label}: URLs a {len(domains)} dominio(s): " + ", ".join(domains[:6]))
    return fails, warns, infos


def scan_tree(root):
    """Escanea todos los ficheros bajo `root`. Devuelve {ruta: (fails, warns, infos)} solo con hallazgos."""
    out = {}
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if not f.is_file() or ".git" in rel.parts:
            continue
        size = f.stat().st_size
        if size > MAX_SCAN_BYTES:
            out[str(rel)] = ([f"demasiado grande para escanear ({size} B); se rechaza en lugar de saltarlo"], [], [])
            continue
        data = f.read_bytes()
        if b"\x00" in data[:8192]:
            out[str(rel)] = ([], ["fichero binario, no escaneable como texto: revisar a mano"], [])
            continue
        fa, wa, inf = scan_text(data.decode("utf-8", errors="replace"), True, "contenido")
        if fa or wa or inf:
            out[str(rel)] = (fa, wa, inf)
    return out


def main():
    ap = argparse.ArgumentParser(description="Escaneo mínimo de seguridad del repositorio")
    ap.add_argument("--dir", default=".", help="carpeta raíz a escanear")
    args = ap.parse_args()
    root = Path(args.dir)
    if not root.is_dir():
        print(f"[ERROR] no existe {root}", file=sys.stderr)
        sys.exit(2)
    n = sum(1 for f in root.rglob("*") if f.is_file() and ".git" not in f.relative_to(root).parts)
    res = scan_tree(root)
    nf = sum(len(v[0]) for v in res.values())
    nw = sum(len(v[1]) for v in res.values())
    for rel, (fa, wa, inf) in res.items():
        for x in fa:
            print(f"FAIL  {rel}: {x}")
        for x in wa:
            print(f"WARN  {rel}: {x}")
        for x in inf:
            print(f"INFO  {rel}: {x}")
    print(f"\nResumen: ficheros escaneados={n} · FAIL={nf} · WARN={nw}")
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
