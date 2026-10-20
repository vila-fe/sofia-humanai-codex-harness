"""Persistent memory for SOFIA coding agents.

The primary API is asynchronous.  It uses Supabase's ``create_async_client``
and awaits every request's ``execute`` method, so network persistence does not
block an agent's event loop.  A small synchronous facade is retained for
existing command-line callers and delegates to this same implementation.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol, TypeVar, cast


class AsyncResponse(Protocol):
    """Subset of a Supabase response used by this module."""

    data: Any


class AsyncRequest(Protocol):
    """Subset of an async Supabase query builder used by this module."""

    async def execute(self) -> AsyncResponse:
        """Execute the request without blocking the caller's event loop."""


class AsyncSupabaseClient(Protocol):
    """Injectable client contract for the async Supabase operations below."""

    def table(self, table_name: str) -> Any:
        """Return an asynchronous table-query builder."""

    def rpc(self, function_name: str, parameters: dict[str, Any]) -> Any:
        """Return an asynchronous RPC-query builder."""


AsyncClientFactory = Callable[[str, str], Awaitable[AsyncSupabaseClient]]
T = TypeVar("T")


class CheckpointRecoveryError(RuntimeError):
    """A durable local checkpoint was absent, corrupt, or cannot be resumed."""


@dataclass(frozen=True)
class RemoteRecord:
    """An existing-schema record that can be removed during compensation."""

    table: str
    id_column: str
    id: str

    def as_dict(self) -> dict[str, str]:
        return {"table": self.table, "id_column": self.id_column, "id": self.id}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RemoteRecord":
        try:
            return cls(
                table=str(value["table"]),
                id_column=str(value["id_column"]),
                id=str(value["id"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise CheckpointRecoveryError("El checkpoint contiene un registro remoto inválido") from error


class StepPersistenceError(RuntimeError):
    """A compound step failed and reports whether remote remnants can remain.

    ``status`` is deliberately machine-readable.  Callers must inspect it
    before retrying: an incomplete compensation has known survivor IDs and the
    checkpoint retains them for ``recover_pending_step``.
    """

    def __init__(
        self,
        original_error: BaseException,
        *,
        survivors: Sequence[RemoteRecord],
        rollback_errors: Sequence[tuple[RemoteRecord, BaseException]],
        mode: str,
    ) -> None:
        self.original_error = original_error
        self.status: dict[str, Any] = {
            "mode": mode,
            "compensation_complete": not survivors,
            "surviving_records": [record.as_dict() for record in survivors],
            "rollback_errors": [
                {"record": record.as_dict(), "error": str(error)}
                for record, error in rollback_errors
            ],
            "original_error": str(original_error),
        }
        message = "No se pudo persistir el paso"
        if survivors:
            message += "; la compensación dejó registros identificados"
        else:
            message += "; la compensación eliminó los registros planificados"
        super().__init__(message)


class SessionCheckpointStore:
    """Crash-safe JSON checkpoint storage for one active agent session.

    ``save`` is synchronous by design so it can also be used by a recovery
    command.  Async callers must use it via ``asyncio.to_thread``; the loop
    class below does so for every local filesystem operation.
    """

    def __init__(self, directory: str | Path, filename: str = "session-checkpoint.json") -> None:
        self.directory = Path(directory)
        self.path = self.directory / filename

    def save(self, checkpoint: Mapping[str, Any]) -> None:
        """Durably replace the checkpoint using temp-file + fsync + replace."""
        self.directory.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(dict(checkpoint), ensure_ascii=False, sort_keys=True).encode("utf-8")
        temporary_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.directory,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(encoded)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
            self._fsync_directory()
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass

    def load(self) -> Optional[dict[str, Any]]:
        """Load the last durable state, rejecting malformed checkpoint files."""
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as checkpoint_file:
                checkpoint = json.load(checkpoint_file)
        except (OSError, json.JSONDecodeError) as error:
            raise CheckpointRecoveryError(
                f"No se pudo recuperar el checkpoint local {self.path}"
            ) from error
        if not isinstance(checkpoint, dict):
            raise CheckpointRecoveryError("El checkpoint local debe contener un objeto JSON")
        return checkpoint

    def clear(self) -> None:
        """Remove a recovered checkpoint and flush that directory entry."""
        try:
            self.path.unlink()
        except FileNotFoundError:
            return
        self._fsync_directory()

    def _fsync_directory(self) -> None:
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(self.directory, directory_flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


async def _default_async_client_factory(url: str, key: str) -> AsyncSupabaseClient:
    """Create the official async client only when dependency injection is absent."""
    from supabase import create_async_client

    return await create_async_client(url, key)


class AsyncPersistentMemory:
    """Asynchronous, injectable persistence layer over the existing schema.

    Only the schema named in the README is used.  ``atomic_step_rpc`` is
    disabled by default because this repository does not deploy such a
    function.  When enabled, it must name an application-owned *transactional*
    RPC accepting one JSON argument named ``step``; its database transaction
    must insert the supplied ``trace``, ``implementation``, and ``evaluations``
    together.  The sequential fallback never assumes a new column or index and
    compensates by deleting generated-ID records in reverse dependency order.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        *,
        client: Optional[AsyncSupabaseClient] = None,
        client_factory: Optional[AsyncClientFactory] = None,
        atomic_step_rpc: Optional[str] = None,
    ) -> None:
        self._supabase_url = supabase_url
        self._supabase_key = supabase_key
        self._client: Optional[AsyncSupabaseClient] = client
        self._client_factory = client_factory or _default_async_client_factory
        self._client_lock: Optional[asyncio.Lock] = None
        self.atomic_step_rpc = atomic_step_rpc

    async def _get_client(self) -> AsyncSupabaseClient:
        if self._client is not None:
            return self._client
        if not self._supabase_url or not self._supabase_key:
            raise ValueError(
                "Se requiere supabase_url y supabase_key cuando no se inyecta un cliente asíncrono"
            )
        if self._client_lock is None:
            self._client_lock = asyncio.Lock()
        async with self._client_lock:
            if self._client is None:
                self._client = await self._client_factory(self._supabase_url, self._supabase_key)
        return self._client

    @staticmethod
    async def _execute(request: AsyncRequest) -> AsyncResponse:
        """Make the awaited query boundary explicit and uniform."""
        return await request.execute()

    @staticmethod
    def _generate_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _implementation_data(
        self,
        session_id: uuid.UUID,
        artifact_type: str,
        content: str,
        storage_path: Optional[str],
        metadata: Optional[dict[str, Any]],
        artifact_id: uuid.UUID,
    ) -> dict[str, Any]:
        # Hashing can be non-trivial for a large diff, so keep it off the loop.
        content_hash = await asyncio.to_thread(self._generate_content_hash, content)
        return {
            "artifact_id": str(artifact_id),
            "session_id": str(session_id),
            "artifact_type": artifact_type,
            "content_hash": content_hash,
            "content_preview": content[:500],
            "storage_path": storage_path,
            "metadata": metadata or {},
        }

    async def store_session(
        self,
        project_id: str,
        task_signature: str,
        model_used: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        *,
        session_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        session_id = session_id or uuid.uuid4()
        session_data = {
            "session_id": str(session_id),
            "project_id": project_id,
            "task_signature": task_signature,
            "model_used": model_used,
            "metadata": metadata or {},
        }
        client = await self._get_client()
        await self._execute(client.table("agent_sessions").insert(session_data))
        return session_id

    async def store_implementation(
        self,
        session_id: uuid.UUID,
        artifact_type: str,
        content: str,
        storage_path: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        *,
        artifact_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        artifact_id = artifact_id or uuid.uuid4()
        implementation_data = await self._implementation_data(
            session_id,
            artifact_type,
            content,
            storage_path,
            metadata,
            artifact_id,
        )
        client = await self._get_client()
        await self._execute(client.table("implementations").insert(implementation_data))
        return artifact_id

    async def store_evaluation(
        self,
        artifact_id: uuid.UUID,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        evaluator_context: Optional[dict[str, Any]] = None,
        *,
        metric_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        metric_id = metric_id or uuid.uuid4()
        evaluation_data = {
            "metric_id": str(metric_id),
            "artifact_id": str(artifact_id),
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "evaluator_context": evaluator_context or {},
        }
        client = await self._get_client()
        await self._execute(client.table("evaluation_metrics").insert(evaluation_data))
        return metric_id

    async def store_reasoning_trace(
        self,
        session_id: uuid.UUID,
        step_number: int,
        decision_type: str,
        decision_text: str,
        rationale: Optional[str] = None,
        alternatives_rejected: Optional[list[str]] = None,
        *,
        trace_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        trace_id = trace_id or uuid.uuid4()
        trace_data = {
            "trace_id": str(trace_id),
            "session_id": str(session_id),
            "step_number": step_number,
            "decision_type": decision_type,
            "decision_text": decision_text,
            "rationale": rationale,
            "alternatives_rejected": alternatives_rejected or [],
        }
        client = await self._get_client()
        await self._execute(client.table("reasoning_traces").insert(trace_data))
        return trace_id

    async def retrieve_relevant(self, task_signature: str, top_k: int = 5) -> list[dict[str, Any]]:
        client = await self._get_client()
        result = await self._execute(
            client.rpc("find_similar_sessions", {"task_sig": task_signature, "k": top_k})
        )
        return cast(list[dict[str, Any]], result.data or [])

    async def update_session_metrics(
        self,
        session_id: uuid.UUID,
        actions_count: int,
        success_flag: bool,
        total_cost_usd: float,
        avg_latency_ms: float,
    ) -> None:
        client = await self._get_client()
        await self._execute(
            client.table("agent_sessions")
            .update(
                {
                    "actions_count": actions_count,
                    "success_flag": success_flag,
                    "total_cost_usd": total_cost_usd,
                    "avg_latency_ms": avg_latency_ms,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("session_id", str(session_id))
        )

    async def add_supervisor_signal(
        self, session_id: uuid.UUID, trigger: str, action_taken: str
    ) -> None:
        client = await self._get_client()
        result = await self._execute(
            client.table("agent_sessions").select("supervisor_signals").eq("session_id", str(session_id))
        )
        if not result.data:
            raise LookupError(f"No existe la sesión {session_id}")
        signals = list(result.data[0].get("supervisor_signals") or [])
        signals.append(
            {
                "trigger": trigger,
                "action_taken": action_taken,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self._execute(
            client.table("agent_sessions")
            .update({"supervisor_signals": signals, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("session_id", str(session_id))
        )

    async def get_session_artifacts(self, session_id: uuid.UUID) -> list[dict[str, Any]]:
        client = await self._get_client()
        result = await self._execute(
            client.table("implementations").select("*").eq("session_id", str(session_id))
        )
        return cast(list[dict[str, Any]], result.data or [])

    async def get_artifact_evaluations(self, artifact_id: uuid.UUID) -> list[dict[str, Any]]:
        client = await self._get_client()
        result = await self._execute(
            client.table("evaluation_metrics").select("*").eq("artifact_id", str(artifact_id))
        )
        return cast(list[dict[str, Any]], result.data or [])

    async def compensate_records(self, records: Sequence[RemoteRecord]) -> dict[str, Any]:
        """Delete planned records in reverse dependency order and expose failures."""
        client = await self._get_client()
        survivors: list[RemoteRecord] = []
        errors: list[tuple[RemoteRecord, BaseException]] = []
        for record in reversed(records):
            try:
                await self._execute(
                    client.table(record.table).delete().eq(record.id_column, record.id)
                )
            except Exception as error:  # Return recoverable record IDs, never mask the write error.
                survivors.append(record)
                errors.append((record, error))
        return {
            "compensation_complete": not survivors,
            "surviving_records": [record.as_dict() for record in survivors],
            "rollback_errors": [
                {"record": record.as_dict(), "error": str(error)} for record, error in errors
            ],
        }

    async def store_step(
        self,
        *,
        session_id: uuid.UUID,
        step_number: int,
        decision_type: str,
        decision_text: str,
        implementation_content: str,
        artifact_type: str,
        rationale: Optional[str],
        trace_id: uuid.UUID,
        artifact_id: uuid.UUID,
        metrics: Sequence[tuple[uuid.UUID, str, float, str]],
    ) -> None:
        """Persist one logical step safely without altering the deployed schema.

        Generated UUIDs are known before remote I/O.  Thus the sequential path
        can safely attempt deletion of *all* planned rows, including a request
        that may have committed before reporting a transport error.
        """
        trace_record = RemoteRecord("reasoning_traces", "trace_id", str(trace_id))
        artifact_record = RemoteRecord("implementations", "artifact_id", str(artifact_id))
        metric_records = [
            RemoteRecord("evaluation_metrics", "metric_id", str(metric_id))
            for metric_id, _name, _value, _unit in metrics
        ]
        records = [trace_record, artifact_record, *metric_records]
        implementation_data = await self._implementation_data(
            session_id,
            artifact_type,
            implementation_content,
            None,
            None,
            artifact_id,
        )
        trace_data = {
            "trace_id": str(trace_id),
            "session_id": str(session_id),
            "step_number": step_number,
            "decision_type": decision_type,
            "decision_text": decision_text,
            "rationale": rationale,
            "alternatives_rejected": [],
        }
        evaluations = [
            {
                "metric_id": str(metric_id),
                "artifact_id": str(artifact_id),
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "evaluator_context": {},
            }
            for metric_id, metric_name, metric_value, metric_unit in metrics
        ]
        client = await self._get_client()

        if self.atomic_step_rpc:
            try:
                await self._execute(
                    client.rpc(
                        self.atomic_step_rpc,
                        {
                            "step": {
                                "session_id": str(session_id),
                                "step_number": step_number,
                                "trace": trace_data,
                                "implementation": implementation_data,
                                "evaluations": evaluations,
                            }
                        },
                    )
                )
                return
            except Exception as error:
                # The configured RPC is responsible for transactional all-or-nothing semantics.
                raise StepPersistenceError(
                    error,
                    survivors=records,
                    rollback_errors=[],
                    mode="atomic_rpc_unknown",
                ) from error

        try:
            await self._execute(client.table("reasoning_traces").insert(trace_data))
            await self._execute(client.table("implementations").insert(implementation_data))
            for evaluation in evaluations:
                await self._execute(client.table("evaluation_metrics").insert(evaluation))
        except Exception as error:
            compensation = await self.compensate_records(records)
            survivors = [RemoteRecord.from_dict(record) for record in compensation["surviving_records"]]
            rollback_errors = [
                (record, RuntimeError(entry["error"]))
                for record, entry in zip(survivors, compensation["rollback_errors"])
            ]
            raise StepPersistenceError(
                error,
                survivors=survivors,
                rollback_errors=rollback_errors,
                mode="compensated_sequential",
            ) from error


class AsyncAgenticLoopWithMemory:
    """Async agent loop with local recovery for compound persistence writes."""

    def __init__(
        self,
        memory: AsyncPersistentMemory,
        project_id: str,
        task_signature: str,
        *,
        checkpoint_store: Optional[SessionCheckpointStore] = None,
    ) -> None:
        self.memory = memory
        self.project_id = project_id
        self.task_signature = task_signature
        self.session_id: Optional[uuid.UUID] = None
        self.step_counter = 0
        self.checkpoint_store = checkpoint_store or SessionCheckpointStore(".sofia-checkpoints")

    def _checkpoint(self, pending_step: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if self.session_id is None:
            raise CheckpointRecoveryError("No se puede crear un checkpoint sin session_id")
        checkpoint: dict[str, Any] = {
            "version": 1,
            "session_id": str(self.session_id),
            "project_id": self.project_id,
            "task_signature": self.task_signature,
            "step_counter": self.step_counter,
        }
        if pending_step is not None:
            checkpoint["pending_step"] = pending_step
        return checkpoint

    async def _save_checkpoint(self, pending_step: Optional[dict[str, Any]] = None) -> None:
        await asyncio.to_thread(self.checkpoint_store.save, self._checkpoint(pending_step))

    async def start_session(self, model_used: Optional[str] = None) -> uuid.UUID:
        relevant_sessions = await self.memory.retrieve_relevant(self.task_signature, top_k=3)
        self.session_id = await self.memory.store_session(
            project_id=self.project_id,
            task_signature=self.task_signature,
            model_used=model_used,
            metadata={
                "relevant_prior_sessions": [
                    session["session_id"] for session in relevant_sessions if "session_id" in session
                ]
            },
        )
        await self._save_checkpoint()
        if relevant_sessions:
            await self.memory.store_reasoning_trace(
                session_id=self.session_id,
                step_number=0,
                decision_type="plan",
                decision_text=f"Recuperadas {len(relevant_sessions)} sesiones similares",
                rationale="Contexto enriquecido con implementaciones previas",
                alternatives_rejected=[
                    session["task_signature"]
                    for session in relevant_sessions
                    if "task_signature" in session
                ],
            )
        return self.session_id

    async def execute_step(
        self,
        decision_type: str,
        decision_text: str,
        implementation_content: str,
        artifact_type: str = "code",
        evaluation_metrics: Optional[dict[str, float]] = None,
        rationale: Optional[str] = None,
    ) -> dict[str, Any]:
        if self.session_id is None:
            raise RuntimeError("Debe iniciar la sesión antes de ejecutar un paso")
        step_number = self.step_counter + 1
        trace_id = uuid.uuid4()
        artifact_id = uuid.uuid4()
        metrics = [
            (
                uuid.uuid4(),
                metric_name,
                metric_value,
                "score" if "accuracy" in metric_name else "ms",
            )
            for metric_name, metric_value in (evaluation_metrics or {}).items()
        ]
        records = [
            RemoteRecord("reasoning_traces", "trace_id", str(trace_id)).as_dict(),
            RemoteRecord("implementations", "artifact_id", str(artifact_id)).as_dict(),
            *[
                RemoteRecord("evaluation_metrics", "metric_id", str(metric_id)).as_dict()
                for metric_id, _name, _value, _unit in metrics
            ],
        ]
        pending_step = {"status": "pending", "step_number": step_number, "records": records}
        # This durable intent precedes all remote writes and lets a restart clean up unknown state.
        await self._save_checkpoint(pending_step)
        try:
            await self.memory.store_step(
                session_id=self.session_id,
                step_number=step_number,
                decision_type=decision_type,
                decision_text=decision_text,
                implementation_content=implementation_content,
                artifact_type=artifact_type,
                rationale=rationale,
                trace_id=trace_id,
                artifact_id=artifact_id,
                metrics=metrics,
            )
        except StepPersistenceError as error:
            pending_step["status"] = "failed"
            pending_step["persistence_status"] = error.status
            await self._save_checkpoint(pending_step)
            raise
        except Exception as error:
            pending_step["status"] = "failed"
            pending_step["persistence_status"] = {
                "mode": "unexpected",
                "compensation_complete": False,
                "surviving_records": records,
                "original_error": str(error),
            }
            await self._save_checkpoint(pending_step)
            raise StepPersistenceError(
                error,
                survivors=[RemoteRecord.from_dict(record) for record in records],
                rollback_errors=[],
                mode="unexpected",
            ) from error

        self.step_counter = step_number
        await self._save_checkpoint()
        return {"trace_id": trace_id, "artifact_id": artifact_id, "step_number": step_number}

    @classmethod
    async def resume_from_checkpoint(
        cls,
        memory: AsyncPersistentMemory,
        *,
        checkpoint_store: SessionCheckpointStore,
    ) -> "AsyncAgenticLoopWithMemory":
        checkpoint = await asyncio.to_thread(checkpoint_store.load)
        if checkpoint is None:
            raise CheckpointRecoveryError("No existe un checkpoint local para recuperar")
        try:
            session_id = uuid.UUID(str(checkpoint["session_id"]))
            project_id = str(checkpoint["project_id"])
            task_signature = str(checkpoint["task_signature"])
            step_counter = int(checkpoint["step_counter"])
        except (KeyError, TypeError, ValueError) as error:
            raise CheckpointRecoveryError("El checkpoint local no describe una sesión recuperable") from error
        if step_counter < 0:
            raise CheckpointRecoveryError("El checkpoint contiene un contador de pasos negativo")
        loop = cls(
            memory,
            project_id=project_id,
            task_signature=task_signature,
            checkpoint_store=checkpoint_store,
        )
        loop.session_id = session_id
        loop.step_counter = step_counter
        return loop

    async def recover_pending_step(self) -> dict[str, Any]:
        """Retry the stored compensation before allowing a new step after restart."""
        checkpoint = await asyncio.to_thread(self.checkpoint_store.load)
        if checkpoint is None:
            raise CheckpointRecoveryError("No existe un checkpoint local para recuperar")
        pending_step = checkpoint.get("pending_step")
        if pending_step is None:
            return {"compensation_complete": True, "surviving_records": [], "rollback_errors": []}
        if not isinstance(pending_step, dict) or not isinstance(pending_step.get("records"), list):
            raise CheckpointRecoveryError("El checkpoint contiene un paso pendiente inválido")
        records = [RemoteRecord.from_dict(record) for record in pending_step["records"]]
        compensation = await self.memory.compensate_records(records)
        if compensation["compensation_complete"]:
            await self._save_checkpoint()
        else:
            pending_step["status"] = "recovery_failed"
            pending_step["records"] = compensation["surviving_records"]
            pending_step["persistence_status"] = compensation
            await self._save_checkpoint(pending_step)
        return compensation

    async def check_supervisor_signals(self, stagnation_threshold: int = 10) -> Optional[str]:
        if self.session_id is None:
            raise RuntimeError("Debe iniciar la sesión antes de comprobar señales del supervisor")
        artifacts = await self.memory.get_session_artifacts(self.session_id)
        if len(artifacts) < stagnation_threshold:
            return None
        recent_evals: list[float] = []
        for artifact in artifacts[-stagnation_threshold:]:
            evals = await self.memory.get_artifact_evaluations(uuid.UUID(str(artifact["artifact_id"])))
            if evals:
                recent_evals.append(max(float(evaluation["metric_value"]) for evaluation in evals))
        if len(recent_evals) < stagnation_threshold:
            return None
        if max(recent_evals) - min(recent_evals) < 0.01:
            await self.memory.add_supervisor_signal(
                session_id=self.session_id,
                trigger="stagnation",
                action_taken="redirect_strategy",
            )
            return "stagnation_detected"
        return None

    async def finalize_session(
        self, success_flag: bool, total_cost_usd: float, avg_latency_ms: float
    ) -> None:
        if self.session_id is None:
            raise RuntimeError("Debe iniciar la sesión antes de finalizarla")
        await self.memory.update_session_metrics(
            session_id=self.session_id,
            actions_count=self.step_counter,
            success_flag=success_flag,
            total_cost_usd=total_cost_usd,
            avg_latency_ms=avg_latency_ms,
        )


def _run_sync(awaitable: Awaitable[T]) -> T:
    """Run an async API for legacy synchronous callers, never inside an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    if hasattr(awaitable, "close"):
        awaitable.close()  # type: ignore[attr-defined]
    raise RuntimeError("Use AsyncPersistentMemory inside an active event loop")


class PersistentMemory:
    """Compatibility facade; all persistence behavior lives in AsyncPersistentMemory."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        *,
        client: Optional[AsyncSupabaseClient] = None,
        client_factory: Optional[AsyncClientFactory] = None,
        atomic_step_rpc: Optional[str] = None,
    ) -> None:
        self.async_memory = AsyncPersistentMemory(
            supabase_url,
            supabase_key,
            client=client,
            client_factory=client_factory,
            atomic_step_rpc=atomic_step_rpc,
        )

    def _generate_content_hash(self, content: str) -> str:
        return self.async_memory._generate_content_hash(content)

    def store_session(self, *args: Any, **kwargs: Any) -> uuid.UUID:
        return _run_sync(self.async_memory.store_session(*args, **kwargs))

    def store_implementation(self, *args: Any, **kwargs: Any) -> uuid.UUID:
        return _run_sync(self.async_memory.store_implementation(*args, **kwargs))

    def store_evaluation(self, *args: Any, **kwargs: Any) -> uuid.UUID:
        return _run_sync(self.async_memory.store_evaluation(*args, **kwargs))

    def store_reasoning_trace(self, *args: Any, **kwargs: Any) -> uuid.UUID:
        return _run_sync(self.async_memory.store_reasoning_trace(*args, **kwargs))

    def retrieve_relevant(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return _run_sync(self.async_memory.retrieve_relevant(*args, **kwargs))

    def update_session_metrics(self, *args: Any, **kwargs: Any) -> None:
        _run_sync(self.async_memory.update_session_metrics(*args, **kwargs))

    def add_supervisor_signal(self, *args: Any, **kwargs: Any) -> None:
        _run_sync(self.async_memory.add_supervisor_signal(*args, **kwargs))

    def get_session_artifacts(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return _run_sync(self.async_memory.get_session_artifacts(*args, **kwargs))

    def get_artifact_evaluations(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return _run_sync(self.async_memory.get_artifact_evaluations(*args, **kwargs))


class AgenticLoopWithMemory:
    """Synchronous compatibility facade backed by AsyncAgenticLoopWithMemory."""

    def __init__(
        self,
        memory: PersistentMemory | AsyncPersistentMemory,
        project_id: str,
        task_signature: str,
        *,
        checkpoint_store: Optional[SessionCheckpointStore] = None,
    ) -> None:
        self.memory = memory
        async_memory = memory.async_memory if isinstance(memory, PersistentMemory) else memory
        self.async_loop = AsyncAgenticLoopWithMemory(
            async_memory,
            project_id,
            task_signature,
            checkpoint_store=checkpoint_store,
        )

    @property
    def session_id(self) -> Optional[uuid.UUID]:
        return self.async_loop.session_id

    @property
    def step_counter(self) -> int:
        return self.async_loop.step_counter

    def start_session(self, model_used: Optional[str] = None) -> uuid.UUID:
        return _run_sync(self.async_loop.start_session(model_used=model_used))

    def execute_step(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return _run_sync(self.async_loop.execute_step(*args, **kwargs))

    def check_supervisor_signals(self, stagnation_threshold: int = 10) -> Optional[str]:
        return _run_sync(self.async_loop.check_supervisor_signals(stagnation_threshold))

    def finalize_session(self, success_flag: bool, total_cost_usd: float, avg_latency_ms: float) -> None:
        _run_sync(self.async_loop.finalize_session(success_flag, total_cost_usd, avg_latency_ms))


def _start_session_from_env() -> None:
    """Create a session from SUPABASE_URL/SUPABASE_KEY environment variables."""
    import sys

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    project_id = os.environ.get("PROJECT_ID")
    task_signature = os.environ.get("TASK_SIGNATURE")
    model_used = os.environ.get("MODEL_USED")

    missing = [
        name
        for name, value in [
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_KEY (o SUPABASE_SERVICE_ROLE_KEY)", supabase_key),
            ("PROJECT_ID", project_id),
            ("TASK_SIGNATURE", task_signature),
        ]
        if not value
    ]
    if missing:
        print(
            f"No se pudo arrancar la sesión: faltan variables de entorno: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    memory = PersistentMemory(supabase_url=supabase_url, supabase_key=supabase_key)
    loop = AgenticLoopWithMemory(memory=memory, project_id=project_id, task_signature=task_signature)
    print(loop.start_session(model_used=model_used))


if __name__ == "__main__":
    _start_session_from_env()
