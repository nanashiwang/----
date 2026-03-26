from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.enums import FlowType, MessageType, RecommendationAction, RiskLevel
from core.ids import generate_prefixed_id
from core.time import utcnow
from domain.schemas import EvidenceRef


class AgentMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: generate_prefixed_id('msg'))
    run_id: str
    sender: str
    receiver: str
    flow_type: FlowType
    message_type: MessageType
    symbol: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class AgentResult(BaseModel):
    agent_name: str
    run_id: str
    symbol: str
    stance: str
    score: float
    summary: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_flags: List[str] = Field(default_factory=list)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


class ArbitrationResult(BaseModel):
    run_id: str
    symbol: str
    action: RecommendationAction
    final_score: float
    component_scores: Dict[str, float] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_flags: List[str] = Field(default_factory=list)
    explanation: str = ''
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
