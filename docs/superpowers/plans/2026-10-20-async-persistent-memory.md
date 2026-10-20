# Async Persistent Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocking persistence path with an injectable asynchronous Supabase interface that preserves session data safely when a multi-write step fails or a process restarts.

**Architecture:** `AsyncPersistentMemory` owns all Supabase calls and accepts an already-created async client or lazily awaits the official `create_async_client` factory. `AsyncAgenticLoopWithMemory` stages a local durable checkpoint before every compound step, delegates an optional application-provided transactional RPC when configured, and otherwise performs compensating deletes in reverse dependency order. Thin synchronous facades call the same async implementation, so no persistence logic is duplicated.

**Tech Stack:** Python 3.11+, `supabase` async client, standard-library `unittest.IsolatedAsyncioTestCase`, atomic JSON checkpoints using `fsync` and `os.replace`.

**Spec:** User task: asynchronous `src/persistent_memory.py` refactor with TDD, injectable async Supabase access, step atomicity/compensation, local crash checkpoints, reproducible installation, local commits only.

## Global Constraints

- Work only in `/home/ubuntu/repo-audit-08-sofia-humanai-codex-harness`.
- Write failing tests before their corresponding production behavior and observe the expected failure.
- Do not contact a real Supabase service in tests.
- Use `await ...execute()` for every asynchronous persistence request; never use blocking I/O in async paths.
- Do not assume or add database columns, constraints, or RPCs beyond the README’s listed schema.
- An application-specific transactional RPC is opt-in only; without one, failed compound writes must compensate or expose all surviving record identifiers.
- Local checkpoint writes must write a temporary file, flush and `fsync` it, atomically replace the target, and support loading/resume.
- Pin runtime and test dependencies in `pyproject.toml`; do not commit credentials, virtual environments, or build output.
- Use branch `refactor/async-persistent-memory`, create atomic local commits, and do not push.

---

### Task 1: Test and packaging scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `tests/test_persistent_memory.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: existing `PersistentMemory` module import path.
- Produces: an offline fake async Supabase client and a test command runnable from a clean checkout.

- [ ] **Step 1: Write failing async interface tests**

```python
async def test_store_session_awaits_an_injected_async_client_without_network():
    client = FakeAsyncClient()
    memory = AsyncPersistentMemory(client=client)

    session_id = await memory.store_session("project-a", "task-a")

    assert client.inserted["agent_sessions"][0]["session_id"] == str(session_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_persistent_memory.AsyncPersistentMemoryTests.test_store_session_awaits_an_injected_async_client_without_network -v`
Expected: FAIL because `AsyncPersistentMemory` is not yet defined.

- [ ] **Step 3: Add project dependencies and test discovery configuration**

```toml
[project]
requires-python = ">=3.11"
dependencies = ["supabase==2.33.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Add `.venv/`, `__pycache__/`, and test caches to `.gitignore`.

- [ ] **Step 4: Add README installation and async use instructions**

```bash
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
```

- [ ] **Step 5: Commit the independent test/tooling scaffold**

```bash
git add pyproject.toml .gitignore tests/test_persistent_memory.py README.md
git commit -m "test: define async persistent memory contract"
```

### Task 2: Injectable asynchronous persistence layer

**Files:**
- Modify: `src/persistent_memory.py`
- Modify: `tests/test_persistent_memory.py`

**Interfaces:**
- Consumes: async Supabase client methods `table`, `rpc`, and query builders with awaitable `execute`.
- Produces: `AsyncPersistentMemory(client=...)`, `await store_session(...)`, `await retrieve_relevant(...)`, and async equivalents for the existing record operations.

- [ ] **Step 1: Write failing tests for lazy factory use and awaitable reads/writes**

```python
async def test_retrieve_relevant_awaits_rpc_response_and_returns_data():
    client = FakeAsyncClient(rpc_data=[{"session_id": "prior"}])
    memory = AsyncPersistentMemory(client=client)

    assert await memory.retrieve_relevant("task-a", top_k=3) == [{"session_id": "prior"}]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `python -m unittest tests.test_persistent_memory.AsyncPersistentMemoryTests -v`
Expected: FAIL because the awaited methods do not exist.

- [ ] **Step 3: Implement only the async client boundary and record operations**

```python
async def _execute(self, request: AsyncRequest) -> Any:
    return await request.execute()
```

Use a lazily awaited `create_async_client` factory only when no injected client is supplied. Preserve the existing table names and payload columns.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `python -m unittest tests.test_persistent_memory.AsyncPersistentMemoryTests -v`
Expected: PASS.

- [ ] **Step 5: Commit the async persistence layer**

```bash
git add src/persistent_memory.py tests/test_persistent_memory.py
git commit -m "refactor: add injectable async Supabase persistence"
```

### Task 3: Durable checkpoints and safe compound step persistence

**Files:**
- Modify: `src/persistent_memory.py`
- Modify: `tests/test_persistent_memory.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `AsyncPersistentMemory` and a path supplied to `SessionCheckpointStore`.
- Produces: `AsyncAgenticLoopWithMemory`, `SessionCheckpointStore.load`, `AsyncAgenticLoopWithMemory.resume_from_checkpoint`, `recover_pending_step`, and `StepPersistenceError.status`.

- [ ] **Step 1: Write failing tests for rollback, explicit residual state, and checkpoint recovery**

```python
async def test_execute_step_compensates_written_trace_when_artifact_insert_fails(tmp_path):
    loop = await started_loop(FakeAsyncClient(fail_insert_for="implementations"), tmp_path)

    with self.assertRaises(StepPersistenceError) as raised:
        await loop.execute_step("fix", "apply patch", "diff")

    assert raised.exception.status["compensation_complete"] is True
    assert loop.step_counter == 0
```

```python
def test_checkpoint_store_recovers_last_durable_session_state(tmp_path):
    store = SessionCheckpointStore(tmp_path)
    store.save({"session_id": "00000000-0000-0000-0000-000000000001", "step_counter": 2})

    assert store.load()["step_counter"] == 2
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run: `python -m unittest tests.test_persistent_memory.SafeStepPersistenceTests tests.test_persistent_memory.CheckpointTests -v`
Expected: FAIL because safe step composition and checkpoint classes do not exist.

- [ ] **Step 3: Implement the minimal safe compound-write behavior**

```python
try:
    await self._insert_trace(...)
    await self._insert_implementation(...)
    await self._insert_metrics(...)
except Exception as write_error:
    rollback_failures = await self._delete_written_records_in_reverse_order(written)
    raise StepPersistenceError(written, rollback_failures) from write_error
```

Before a compound write, durably store all generated IDs and the pending step. On success mark it complete. On failure retain the durable state and make `recover_pending_step` delete known IDs before clearing it. If `atomic_step_rpc` is explicitly configured, call it instead; it is an application-owned transactional function and is not assumed to exist in the supplied schema.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `python -m unittest tests.test_persistent_memory.SafeStepPersistenceTests tests.test_persistent_memory.CheckpointTests -v`
Expected: PASS.

- [ ] **Step 5: Commit safe writes and documentation**

```bash
git add src/persistent_memory.py tests/test_persistent_memory.py README.md
git commit -m "feat: checkpoint and compensate async step persistence"
```

### Task 4: Synchronous compatibility and full verification

**Files:**
- Modify: `src/persistent_memory.py`
- Modify: `tests/test_persistent_memory.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `AsyncPersistentMemory` and `AsyncAgenticLoopWithMemory`.
- Produces: existing synchronous `PersistentMemory` and `AgenticLoopWithMemory` facades backed by the async implementation, with a clear error when used inside an active event loop.

- [ ] **Step 1: Write a failing compatibility test**

```python
def test_sync_memory_facade_delegates_to_the_async_implementation():
    memory = PersistentMemory(client=FakeAsyncClient())

    session_id = memory.store_session("project-a", "task-a")

    assert isinstance(session_id, uuid.UUID)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest tests.test_persistent_memory.SyncCompatibilityTests -v`
Expected: FAIL because the old constructor does not accept an async injected client.

- [ ] **Step 3: Implement thin delegates only**

```python
def _run_sync(awaitable: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(awaitable)
```

Do not reimplement any Supabase request logic in synchronous methods.

- [ ] **Step 4: Verify the full suite and syntax**

Run: `python -m unittest discover -s tests -v && python -m compileall -q src && git diff --check`
Expected: all tests pass, compilation exits 0, and `git diff --check` prints no whitespace errors.

- [ ] **Step 5: Commit compatibility after verification**

```bash
git add src/persistent_memory.py tests/test_persistent_memory.py README.md
git commit -m "refactor: preserve sync facade over async memory"
```
