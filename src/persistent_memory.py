"""
PersistentMemory — capa de memoria persistente para agentes SOFIA.
Almacena y recupera implementaciones, métricas y razonamientos entre sesiones.

Inspirado en la arquitectura AVO de Nvidia (memoria persistente + supervisor).
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from supabase import create_client, Client


class PersistentMemory:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
    
    def _generate_content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def store_session(
        self,
        project_id: str,
        task_signature: str,
        model_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        session_id = uuid.uuid4()
        session_data = {
            'session_id': str(session_id),
            'project_id': project_id,
            'task_signature': task_signature,
            'model_used': model_used,
            'metadata': metadata or {}
        }
        self.client.table('agent_sessions').insert(session_data).execute()
        return session_id
    
    def store_implementation(
        self,
        session_id: uuid.UUID,
        artifact_type: str,
        content: str,
        storage_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        artifact_id = uuid.uuid4()
        content_hash = self._generate_content_hash(content)
        content_preview = content[:500] if len(content) > 500 else content
        implementation_data = {
            'artifact_id': str(artifact_id),
            'session_id': str(session_id),
            'artifact_type': artifact_type,
            'content_hash': content_hash,
            'content_preview': content_preview,
            'storage_path': storage_path,
            'metadata': metadata or {}
        }
        self.client.table('implementations').insert(implementation_data).execute()
        return artifact_id
    
    def store_evaluation(
        self,
        artifact_id: uuid.UUID,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        evaluator_context: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        metric_id = uuid.uuid4()
        evaluation_data = {
            'metric_id': str(metric_id),
            'artifact_id': str(artifact_id),
            'metric_name': metric_name,
            'metric_value': metric_value,
            'metric_unit': metric_unit,
            'evaluator_context': evaluator_context or {}
        }
        self.client.table('evaluation_metrics').insert(evaluation_data).execute()
        return metric_id
    
    def store_reasoning_trace(
        self,
        session_id: uuid.UUID,
        step_number: int,
        decision_type: str,
        decision_text: str,
        rationale: Optional[str] = None,
        alternatives_rejected: Optional[List[str]] = None
    ) -> uuid.UUID:
        trace_id = uuid.uuid4()
        trace_data = {
            'trace_id': str(trace_id),
            'session_id': str(session_id),
            'step_number': step_number,
            'decision_type': decision_type,
            'decision_text': decision_text,
            'rationale': rationale,
            'alternatives_rejected': alternatives_rejected or []
        }
        self.client.table('reasoning_traces').insert(trace_data).execute()
        return trace_id
    
    def retrieve_relevant(
        self,
        task_signature: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        result = self.client.rpc(
            'find_similar_sessions',
            {'task_sig': task_signature, 'k': top_k}
        ).execute()
        return result.data or []
    
    def update_session_metrics(
        self,
        session_id: uuid.UUID,
        actions_count: int,
        success_flag: bool,
        total_cost_usd: float,
        avg_latency_ms: float
    ) -> None:
        self.client.table('agent_sessions').update({
            'actions_count': actions_count,
            'success_flag': success_flag,
            'total_cost_usd': total_cost_usd,
            'avg_latency_ms': avg_latency_ms,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('session_id', str(session_id)).execute()
    
    def add_supervisor_signal(
        self,
        session_id: uuid.UUID,
        trigger: str,
        action_taken: str
    ) -> None:
        session = self.client.table('agent_sessions').select('supervisor_signals').eq(
            'session_id', str(session_id)
        ).execute().data[0]
        signals = session['supervisor_signals'] or []
        signals.append({
            'trigger': trigger,
            'action_taken': action_taken,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        self.client.table('agent_sessions').update({
            'supervisor_signals': signals,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('session_id', str(session_id)).execute()
    
    def get_session_artifacts(
        self,
        session_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        result = self.client.table('implementations').select('*').eq(
            'session_id', str(session_id)
        ).execute()
        return result.data or []
    
    def get_artifact_evaluations(
        self,
        artifact_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        result = self.client.table('evaluation_metrics').select('*').eq(
            'artifact_id', str(artifact_id)
        ).execute()
        return result.data or []


class AgenticLoopWithMemory:
    def __init__(self, memory: PersistentMemory, project_id: str, task_signature: str):
        self.memory = memory
        self.project_id = project_id
        self.task_signature = task_signature
        self.session_id: Optional[uuid.UUID] = None
        self.step_counter = 0
    
    def start_session(self, model_used: Optional[str] = None) -> uuid.UUID:
        relevant_sessions = self.memory.retrieve_relevant(self.task_signature, top_k=3)
        self.session_id = self.memory.store_session(
            project_id=self.project_id,
            task_signature=self.task_signature,
            model_used=model_used,
            metadata={'relevant_prior_sessions': [s['session_id'] for s in relevant_sessions]}
        )
        if relevant_sessions:
            self.memory.store_reasoning_trace(
                session_id=self.session_id,
                step_number=0,
                decision_type='plan',
                decision_text=f'Recuperadas {len(relevant_sessions)} sesiones similares',
                rationale='Contexto enriquecido con implementaciones previas',
                alternatives_rejected=[s['task_signature'] for s in relevant_sessions]
            )
        return self.session_id
    
    def execute_step(
        self,
        decision_type: str,
        decision_text: str,
        implementation_content: str,
        artifact_type: str = 'code',
        evaluation_metrics: Optional[Dict[str, float]] = None,
        rationale: Optional[str] = None
    ) -> Dict[str, Any]:
        self.step_counter += 1
        trace_id = self.memory.store_reasoning_trace(
            session_id=self.session_id,
            step_number=self.step_counter,
            decision_type=decision_type,
            decision_text=decision_text,
            rationale=rationale
        )
        artifact_id = self.memory.store_implementation(
            session_id=self.session_id,
            artifact_type=artifact_type,
            content=implementation_content
        )
        if evaluation_metrics:
            for metric_name, metric_value in evaluation_metrics.items():
                self.memory.store_evaluation(
                    artifact_id=artifact_id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_unit='score' if 'accuracy' in metric_name else 'ms'
                )
        return {'trace_id': trace_id, 'artifact_id': artifact_id, 'step_number': self.step_counter}
    
    def check_supervisor_signals(self, stagnation_threshold: int = 10) -> Optional[str]:
        artifacts = self.memory.get_session_artifacts(self.session_id)
        if len(artifacts) < stagnation_threshold:
            return None
        recent_evals = []
        for artifact in artifacts[-stagnation_threshold:]:
            evals = self.memory.get_artifact_evaluations(artifact['artifact_id'])
            if evals:
                recent_evals.append(max(e['metric_value'] for e in evals))
        if len(recent_evals) < stagnation_threshold:
            return None
        if max(recent_evals) - min(recent_evals) < 0.01:
            self.memory.add_supervisor_signal(
                session_id=self.session_id,
                trigger='stagnation',
                action_taken='redirect_strategy'
            )
            return 'stagnation_detected'
        return None
    
    def finalize_session(self, success_flag: bool, total_cost_usd: float, avg_latency_ms: float) -> None:
        self.memory.update_session_metrics(
            session_id=self.session_id,
            actions_count=self.step_counter,
            success_flag=success_flag,
            total_cost_usd=total_cost_usd,
            avg_latency_ms=avg_latency_ms
        )
