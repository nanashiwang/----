from __future__ import annotations

from datetime import datetime, timezone

from core.enums import RecommendationAction
from domain.messages import AgentMessage
from domain.schemas import CandidateOut, EvidenceRef


def test_reason_flow_schema_message_and_candidate():
    evidence = EvidenceRef(
        ref_type='news_article',
        title='Sector catalyst',
        source='unit_test',
        excerpt='A catalyst was observed.',
        published_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
    )
    message = AgentMessage(
        run_id='run_test',
        sender='bull_case_agent',
        receiver='moderator_agent',
        flow_type='reason',
        message_type='argument',
        symbol='600519.SH',
        payload={'score': 0.72},
        evidence_refs=[evidence],
    )
    assert message.symbol == '600519.SH'
    candidate = CandidateOut(
        symbol='600519.SH',
        action=RecommendationAction.INCLUDE,
        weight=0.8,
        final_score=0.8,
        evidence_refs=[evidence],
    )
    assert candidate.action == RecommendationAction.INCLUDE
