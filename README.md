# sofia-humanai-codex-harness

**SOFIA Human-AI + Codex Harness Framework** — componente reusable del **Programa SOFIA
Human-AI AVFEARS** para dar memoria persistente entre sesiones a bucles agénticos de codificación
("Codex Harness"): agentes que ejecutan tareas de código de forma iterativa y necesitan recordar
qué se implementó, cómo se evaluó, y por qué se tomó cada decisión, más allá de una sola sesión.

Licencia: Apache 2.0. Único repo público del stack SOFIA — pensado para ser reusable fuera del
programa, no solo como documentación interna.

## Qué hace

Inspirado en la arquitectura AVO de Nvidia (memoria persistente + supervisor), expone dos piezas
asíncronas en [`src/persistent_memory.py`](src/persistent_memory.py):

- **`AsyncPersistentMemory`** — capa de persistencia Supabase inyectable y asíncrona. Guarda
  sesiones de agente, implementaciones (con hash de contenido para deduplicar), métricas de
  evaluación y trazas de razonamiento. Cada petición usa `await ...execute()`; el cliente oficial
  se crea perezosamente con `create_async_client` solo si no se inyecta un cliente compatible.
- **`AsyncAgenticLoopWithMemory`** — envuelve el bucle agéntico: recupera sesiones similares al
  arrancar, registra traza + artefacto + métricas por paso, puede detectar estancamiento, y cierra
  la sesión con coste y latencia agregados.

Los nombres históricos **`PersistentMemory`** y **`AgenticLoopWithMemory`** permanecen como
fachadas síncronas finas sobre la misma implementación asíncrona. Úselos solo desde código que no
tenga un *event loop* activo; dentro de `async def`, use siempre las clases `Async...`.

## Instalación reproducible

Se fijan las versiones directas en `pyproject.toml` y se incluye `uv.lock` para una resolución
reproducible.

```bash
git clone <URL-DEL-REPOSITORIO>
cd sofia-humanai-codex-harness
uv sync --extra test
uv run pytest
```

Alternativa con `pip` (instala las mismas versiones directas, aunque `uv sync` es la ruta
reproducible recomendada):

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest
```

Las pruebas son completamente locales: usan un cliente Supabase asíncrono falso inyectado y no
requieren URL, clave ni red real.

## Uso asíncrono recomendado

```python
from persistent_memory import AsyncAgenticLoopWithMemory, AsyncPersistentMemory


async def run() -> None:
    memory = AsyncPersistentMemory(supabase_url="https://<proyecto>.supabase.co", supabase_key="<key>")
    loop = AsyncAgenticLoopWithMemory(
        memory,
        project_id="sofia-router",
        task_signature="fix-circuit-breaker",
    )

    await loop.start_session(model_used="claude-sonnet-5")
    await loop.execute_step(
        decision_type="fix",
        decision_text="Ajustar umbral del circuit breaker",
        implementation_content="<diff o código>",
        evaluation_metrics={"tests_passing": 1.0},
    )
    if await loop.check_supervisor_signals() == "stagnation_detected":
        ...  # redirigir estrategia
    await loop.finalize_session(success_flag=True, total_cost_usd=0.02, avg_latency_ms=450)
```

Para pruebas o para integrar un cliente ya gestionado, inyéctelo directamente; no se crea ningún
cliente ni se realiza I/O de red en el constructor:

```python
memory = AsyncPersistentMemory(client=my_async_supabase_client)
```

El cliente inyectado debe proporcionar `table(...)` y `rpc(...)`, cuyos *query builders* tienen un
método `async execute()` compatible con `supabase.AsyncClient`.

## Pasos compuestos: consistencia y recuperación

`execute_step` escribe tres tipos de filas existentes: `reasoning_traces`, `implementations` y
`evaluation_metrics`. No se añade ninguna columna, tabla, índice ni función SQL al esquema del
proyecto.

1. Antes de I/O remoto, genera los UUID de las filas planeadas y guarda un checkpoint local.
2. **Por defecto**, inserta de forma secuencial y, si alguna operación falla, intenta eliminar
   **todas** las filas planeadas en orden inverso de dependencias. Esto cubre incluso una petición
   cuyo servidor pudo haber confirmado antes de comunicar un error de transporte.
3. Si la compensación falla, lanza `StepPersistenceError`. Su atributo `status` contiene
   `compensation_complete`, `surviving_records` (tabla, columna e ID) y los errores de rollback;
   el fallo nunca se oculta.

### RPC transaccional opcional

El único RPC asumido por este repositorio es `find_similar_sessions`. No se entrega ni se presupone
una migración para un RPC de pasos. Si su proyecto **ya dispone** de una función transaccional que
puede insertar un paso completo, habilítela explícitamente:

```python
memory = AsyncPersistentMemory(
    supabase_url="https://<proyecto>.supabase.co",
    supabase_key="<key>",
    atomic_step_rpc="nombre_de_su_rpc_transaccional",
)
```

Al habilitarla, la librería llama `rpc(nombre, {"step": ...})`, donde `step` contiene los objetos
`trace`, `implementation` y `evaluations` con las columnas ya existentes. La función es propiedad
del despliegue de la aplicación y **debe** ejecutar esos inserts en una única transacción. No active
esta opción para una RPC que no respete ese contrato. Si la llamada RPC devuelve un error, se expone
un `StepPersistenceError` con estado `atomic_rpc_unknown` y los IDs planeados se conservan en el
checkpoint para revisión/recuperación.

### Checkpoints locales de sesión

Por defecto se usa `.sofia-checkpoints/session-checkpoint.json` (excluido de Git), o puede
proporcionar `SessionCheckpointStore` apuntando a un directorio controlado. Cada actualización
serializa JSON a un temporal en el mismo directorio, hace `flush` + `fsync`, usa `os.replace` y hace
`fsync` del directorio. La escritura de archivos se ejecuta con `asyncio.to_thread`, por lo que no
bloquea el *event loop* del bucle agéntico.

Tras un apagado durante un paso, cargue el checkpoint y complete primero la compensación explícita:

```python
from persistent_memory import AsyncAgenticLoopWithMemory, SessionCheckpointStore

store = SessionCheckpointStore("/ruta/privada/a/checkpoints")
loop = await AsyncAgenticLoopWithMemory.resume_from_checkpoint(memory, checkpoint_store=store)
result = await loop.recover_pending_step()
if not result["compensation_complete"]:
    # Revisar result["surviving_records"] antes de reintentar.
    raise RuntimeError(result)
```

La recuperación no borra datos automáticamente al cargar: `recover_pending_step()` es la acción
explícita que intenta borrar los UUID del paso pendiente. Esto evita esconder efectos remotos ante
un reinicio y deja evidencia recuperable para el operador.

## Esquema Supabase necesario

Se requieren las tablas `agent_sessions`, `implementations`, `evaluation_metrics` y
`reasoning_traces`, más la función RPC `find_similar_sessions`. El esquema y sus migraciones no se
incluyen en este repositorio; se asumen desplegados en el proyecto Supabase del Programa SOFIA.

## Estado

La capa de memoria es async-first, se prueba sin red y conserva una ruta síncrona de compatibilidad
para invocaciones de CLI existentes. No se incluye configuración de CI en este cambio.
