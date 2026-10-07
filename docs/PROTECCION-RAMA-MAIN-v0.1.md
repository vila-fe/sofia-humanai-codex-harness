# Protección de la rama `main` — repo público del harness (v0.1, 07/10/2026)

**Bloque de Procedencia (DEC-TRAZ-REG-001)**
- Origen registro: Claude (AVFrere) · Clave de sesión: S-20261007-CLA.
- Propósito: dejar por escrito el compromiso intermedio de protección de `main` decidido por AVF el 07/10/2026 (camino B) y los pasos para activarlo en este repo, porque Claude no tiene permiso de administrador sobre la configuración de GitHub.
- Estado: **DECIDIDA, NO APLICADA.** La configuración de GitHub la hace AVF.
- Guía hermana, más extensa, en el repo privado `sofia-human-ai-avf` (`docs/PROTECCION-RAMA-MAIN-v0.1.md`).

## 1. Qué se decide

| Regla | Aplicar |
|---|---|
| Exigir PR (sin push directo a `main`) | Sí |
| Bloquear el push forzado y el borrado de `main` | Sí |
| Comprobación obligatoria `escaneo-seguridad` | Sí |
| Exigir aprobaciones humanas dentro de GitHub | **No** (los PR salen con la cuenta de AVF y GitHub no deja aprobar el propio PR: bloquearía todas las fusiones) |

## 2. Orden de activación

1. Fusionar el PR que añade el flujo `.github/workflows/escaneo-seguridad.yml` y el script `scripts/sofia_escaneo_seguridad.py`.
2. Comprobar en *Actions* que `escaneo-seguridad` salió en verde sobre `main`.
3. *Settings → Rules → Rulesets → New branch ruleset* sobre `main`: PR obligatorio con 0 aprobaciones, comprobación `escaneo-seguridad`, bloquear push forzado, restringir borrado. Al ser repo público, está disponible con el plan gratuito.
4. *Settings → Actions → General*: dejar activada la aprobación manual de flujos para colaboradores nuevos (un PR de un fork no debe correr nada sin tu visto bueno).

## 3. Límites y riesgos

- **Repo público:** todo su contenido lo lee cualquiera. Escaneo del 07/10/2026 con el mismo código: 0 secretos, 0 inyecciones. El clon era superficial, así que el historial anterior no se pudo revisar.
- **Dos copias del código de escaneo.** `scripts/sofia_escaneo_seguridad.py` se extrajo del auditor del repo privado (v0.2). Si cambia allí, hay que copiarlo aquí; pueden desincronizarse.
- **Detecta patrones, no el sentido.** Una instrucción dañina redactada con naturalidad no salta, ni tampoco los homoglifos. No sustituye la lectura humana.
- **Quien pueda modificar el flujo o el script en un PR podría hacer pasar el control en falso.** Los cambios en `.github/` y en el script deben leerse a mano antes de fusionar. Claude no los fusiona sin OK explícito de AVF (`DEC-NOFUSION-CRITICOS-001`).
- **La regla no impide que Claude fusione** por el conector con la misma cuenta que AVF; el segundo control es el escaneo, no una persona. Lo que mantiene humana la fusión es esa norma de conducta de Claude.
- **Ejecución semanal programada:** control detectivo. En repos públicos GitHub puede desactivarla tras un periodo sin actividad; se reactiva a mano en *Actions*.
