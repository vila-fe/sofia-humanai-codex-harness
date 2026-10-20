"""Offline contract tests for async persistent memory.

The fake client records only queries whose async ``execute`` coroutine is
awaited. It deliberately has no network behavior.
"""

from __future__ import annotations

import copy
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, Optional

from persistent_memory import (
    AsyncAgenticLoopWithMemory,
    AsyncPersistentMemory,
    PersistentMemory,
    SessionCheckpointStore,
    StepPersistenceError,
)


class FakeResponse:
    def __init__(self, data: Optional[list[dict[str, Any]]] = None):
        self.data = data if data is not None else []


class FakeAsyncRequest:
    """Small async PostgREST-compatible request fake for boundary tests."""

    def __init__(self, client: "FakeAsyncClient", table: str, operation: str = "select"):
        self.client = client
        self.table_name = table
        self.operation = operation
        self.payload: Any = None
        self.filters: dict[str, Any] = {}

    def insert(self, payload: dict[str, Any]) -> "FakeAsyncRequest":
        self.operation = "insert"
        self.payload = copy.deepcopy(payload)
        return self

    def update(self, payload: dict[str, Any]) -> "FakeAsyncRequest":
        self.operation = "update"
        self.payload = copy.deepcopy(payload)
        return self

    def delete(self) -> "FakeAsyncRequest":
        self.operation = "delete"
        return self

    def select(self, _columns: str) -> "FakeAsyncRequest":
        self.operation = "select"
        return self

    def eq(self, column: str, value: Any) -> "FakeAsyncRequest":
        self.filters[column] = value
        return self

    async def execute(self) -> FakeResponse:
        self.client.executed.append(
            (self.table_name, self.operation, copy.deepcopy(self.payload), dict(self.filters))
        )
        if (self.table_name, self.operation) in self.client.failures:
            raise RuntimeError(f"forced {self.operation} failure for {self.table_name}")

        rows = self.client.rows.setdefault(self.table_name, [])
        if self.operation == "insert":
            rows.append(copy.deepcopy(self.payload))
            return FakeResponse([copy.deepcopy(self.payload)])
        if self.operation == "delete":
            kept = [row for row in rows if not self._matches(row)]
            deleted = [row for row in rows if self._matches(row)]
            self.client.rows[self.table_name] = kept
            return FakeResponse(deleted)
        if self.operation == "update":
            changed = []
            for row in rows:
                if self._matches(row):
                    row.update(copy.deepcopy(self.payload))
                    changed.append(copy.deepcopy(row))
            return FakeResponse(changed)
        return FakeResponse([copy.deepcopy(row) for row in rows if self._matches(row)])

    def _matches(self, row: dict[str, Any]) -> bool:
        return all(row.get(column) == value for column, value in self.filters.items())


class FakeAsyncClient:
    """Network-free subset of the Supabase async client used by this module."""

    def __init__(
        self,
        *,
        rpc_data: Optional[list[dict[str, Any]]] = None,
        failures: Optional[set[tuple[str, str]]] = None,
    ):
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self.rpc_data = rpc_data if rpc_data is not None else []
        self.failures = failures if failures is not None else set()
        self.executed: list[tuple[str, str, Any, dict[str, Any]]] = []
        self.rpc_calls: list[tuple[str, dict[str, Any]]] = []

    def table(self, table_name: str) -> FakeAsyncRequest:
        return FakeAsyncRequest(self, table_name)

    def rpc(self, function_name: str, parameters: dict[str, Any]) -> FakeAsyncRequest:
        self.rpc_calls.append((function_name, copy.deepcopy(parameters)))
        request = FakeAsyncRequest(self, f"rpc:{function_name}", operation="rpc")

        async def execute_rpc() -> FakeResponse:
            self.executed.append((request.table_name, "rpc", copy.deepcopy(parameters), {}))
            if (request.table_name, "rpc") in self.failures:
                raise RuntimeError(f"forced RPC failure for {function_name}")
            return FakeResponse(copy.deepcopy(self.rpc_data))

        request.execute = execute_rpc  # type: ignore[method-assign]
        return request


class AsyncPersistentMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_session_awaits_injected_client_without_network(self) -> None:
        """Removing ``await execute`` leaves the fake empty and fails this test."""
        client = FakeAsyncClient()
        memory = AsyncPersistentMemory(client=client)

        session_id = await memory.store_session("project-a", "task-a", model_used="model-a")

        self.assertIsInstance(session_id, uuid.UUID)
        self.assertEqual(
            client.rows["agent_sessions"],
            [
                {
                    "session_id": str(session_id),
                    "project_id": "project-a",
                    "task_signature": "task-a",
                    "model_used": "model-a",
                    "metadata": {},
                }
            ],
        )
        self.assertEqual(client.executed[0][0:2], ("agent_sessions", "insert"))

    async def test_lazily_creates_client_with_injected_async_factory(self) -> None:
        client = FakeAsyncClient()
        factory_calls: list[tuple[str, str]] = []

        async def factory(url: str, key: str) -> FakeAsyncClient:
            factory_calls.append((url, key))
            return client

        memory = AsyncPersistentMemory(
            supabase_url="https://example.test",
            supabase_key="test-key",
            client_factory=factory,
        )
        await memory.store_session("project-a", "task-a")

        self.assertEqual(factory_calls, [("https://example.test", "test-key")])
        self.assertEqual(len(client.rows["agent_sessions"]), 1)

    async def test_retrieve_relevant_awaits_rpc_and_returns_response_data(self) -> None:
        client = FakeAsyncClient(rpc_data=[{"session_id": "prior-session"}])
        memory = AsyncPersistentMemory(client=client)

        relevant = await memory.retrieve_relevant("task-a", top_k=3)

        self.assertEqual(relevant, [{"session_id": "prior-session"}])
        self.assertEqual(client.rpc_calls, [("find_similar_sessions", {"task_sig": "task-a", "k": 3})])
        self.assertEqual(client.executed[-1][0:2], ("rpc:find_similar_sessions", "rpc"))

    async def test_implementation_keeps_existing_schema_payload_and_hashes_content(self) -> None:
        client = FakeAsyncClient()
        memory = AsyncPersistentMemory(client=client)
        session_id = uuid.UUID("00000000-0000-0000-0000-000000000011")

        artifact_id = await memory.store_implementation(session_id, "code", "print('safe')")

        row = client.rows["implementations"][0]
        self.assertEqual(row["artifact_id"], str(artifact_id))
        self.assertEqual(row["session_id"], str(session_id))
        self.assertEqual(row["content_hash"], "5f7b503abc5131378440c2e20e25580e5333efbe87e8d8c3f0b8d976e22a8147")
        self.assertNotIn("step_id", row)


class SafeStepPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addAsyncCleanup(self._cleanup_directory)
        self.store = SessionCheckpointStore(Path(self.directory.name))
        self.client = FakeAsyncClient()
        self.memory = AsyncPersistentMemory(client=self.client)
        self.loop = AsyncAgenticLoopWithMemory(
            self.memory,
            project_id="project-a",
            task_signature="task-a",
            checkpoint_store=self.store,
        )
        await self.loop.start_session()

    async def _cleanup_directory(self) -> None:
        self.directory.cleanup()

    async def test_execute_step_compensates_trace_when_artifact_insert_fails(self) -> None:
        """A failure after trace insertion must not leave a partial remote step."""
        self.client.failures.add(("implementations", "insert"))

        with self.assertRaises(StepPersistenceError) as raised:
            await self.loop.execute_step("fix", "apply patch", "diff")

        self.assertTrue(raised.exception.status["compensation_complete"])
        self.assertEqual(raised.exception.status["surviving_records"], [])
        self.assertEqual(self.client.rows["reasoning_traces"], [])
        self.assertEqual(self.loop.step_counter, 0)
        self.assertEqual(self.store.load()["pending_step"]["status"], "failed")

    async def test_execute_step_exposes_survivor_when_compensation_fails(self) -> None:
        """A failed delete must remain observable rather than being concealed."""
        self.client.failures.update(
            {("implementations", "insert"), ("reasoning_traces", "delete")}
        )

        with self.assertRaises(StepPersistenceError) as raised:
            await self.loop.execute_step("fix", "apply patch", "diff")

        self.assertFalse(raised.exception.status["compensation_complete"])
        self.assertEqual(
            raised.exception.status["surviving_records"],
            [{"table": "reasoning_traces", "id_column": "trace_id", "id": self.client.rows["reasoning_traces"][0]["trace_id"]}],
        )
        self.assertIn("pending_step", self.store.load())

    async def test_explicit_atomic_rpc_avoids_schema_specific_multi_table_writes(self) -> None:
        """The optional RPC is only used when an application explicitly enables it."""
        rpc_memory = AsyncPersistentMemory(client=self.client, atomic_step_rpc="persist_agent_step")
        rpc_loop = AsyncAgenticLoopWithMemory(
            rpc_memory,
            project_id="project-b",
            task_signature="task-b",
            checkpoint_store=self.store,
        )
        await rpc_loop.start_session()

        result = await rpc_loop.execute_step("plan", "atomic path", "content", evaluation_metrics={"accuracy": 1.0})

        self.assertEqual(result["step_number"], 1)
        self.assertEqual(self.client.rpc_calls[-1][0], "persist_agent_step")
        self.assertEqual(self.client.rows.get("reasoning_traces", []), [])
        self.assertEqual(self.client.rows.get("implementations", []), [])
        self.assertEqual(self.client.rows.get("evaluation_metrics", []), [])

    async def test_resume_and_recover_pending_step_deletes_known_survivor(self) -> None:
        self.client.failures.update(
            {("implementations", "insert"), ("reasoning_traces", "delete")}
        )
        with self.assertRaises(StepPersistenceError):
            await self.loop.execute_step("fix", "apply patch", "diff")
        self.client.failures.clear()

        restored = await AsyncAgenticLoopWithMemory.resume_from_checkpoint(
            self.memory,
            checkpoint_store=self.store,
        )
        recovery = await restored.recover_pending_step()

        self.assertTrue(recovery["compensation_complete"])
        self.assertEqual(self.client.rows["reasoning_traces"], [])
        self.assertNotIn("pending_step", self.store.load())
        self.assertEqual(restored.step_counter, 0)


class CheckpointTests(unittest.TestCase):
    def test_checkpoint_store_recovers_last_durable_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SessionCheckpointStore(Path(directory))
            checkpoint = {
                "session_id": "00000000-0000-0000-0000-000000000001",
                "project_id": "project-a",
                "task_signature": "task-a",
                "step_counter": 2,
            }

            store.save(checkpoint)

            self.assertEqual(store.load(), checkpoint)
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])


class SyncCompatibilityTests(unittest.TestCase):
    def test_sync_memory_facade_delegates_to_async_implementation(self) -> None:
        client = FakeAsyncClient()
        memory = PersistentMemory(client=client)

        session_id = memory.store_session("project-a", "task-a")

        self.assertIsInstance(session_id, uuid.UUID)
        self.assertEqual(client.rows["agent_sessions"][0]["session_id"], str(session_id))
