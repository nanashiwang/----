from __future__ import annotations

from core.enums import RecommendationAction, RiskLevel
from domain.messages import ArbitrationResult
from domain.schemas import CandidateOut, EvidenceRef


class ArbitrationService:
    def arbitrate(self, candidate: CandidateOut) -> ArbitrationResult:
        base_score = (
            0.35 * candidate.ml_score
            + 0.20 * candidate.event_score
            + 0.20 * candidate.technical_score
            + 0.15 * candidate.debate_consensus_score
            + 0.10 * candidate.risk_adjusted_score
        )
        final_score = max(
            0.0,
            min(
                1.0,
                base_score + candidate.knowledge_match_score - candidate.knowledge_risk_penalty,
            ),
        )

        component_scores = {
            'ml_score': candidate.ml_score,
            'event_score': candidate.event_score,
            'technical_score': candidate.technical_score,
            'debate_consensus_score': candidate.debate_consensus_score,
            'risk_adjusted_score': candidate.risk_adjusted_score,
            'base_score': round(base_score, 4),
            'knowledge_match_score': round(candidate.knowledge_match_score, 4),
            'knowledge_risk_penalty': round(candidate.knowledge_risk_penalty, 4),
        }

        action = RecommendationAction.WATCH
        explanation = 'Candidate remains on the watch list.'
        risk_level = candidate.risk_level
        risk_flags = list(candidate.risk_flags)
        evidence_refs = list(candidate.evidence_refs)
        knowledge_ref_count = len(candidate.knowledge_refs)
        has_hard_knowledge_risk = (
            'knowledge_high_risk' in risk_flags or candidate.knowledge_risk_penalty >= 0.12
        )

        if candidate.knowledge_conflict_flag and 'knowledge_conflict' not in risk_flags:
            risk_flags.append('knowledge_conflict')

        if not evidence_refs:
            action = RecommendationAction.EXCLUDE
            explanation = 'Missing evidence references; recommendation cannot be included.'
        elif has_hard_knowledge_risk:
            action = RecommendationAction.WATCH if final_score >= 0.40 else RecommendationAction.EXCLUDE
            explanation = (
                f'Cold knowledge matched {knowledge_ref_count} items and flagged a high-risk pattern; '
                f'include is downgraded to {action.value}.'
            )
        elif risk_level == RiskLevel.HIGH or 'high_risk' in risk_flags:
            action = RecommendationAction.WATCH
            explanation = 'Risk is too high for include; downgraded to watch.'
        elif final_score >= 0.65:
            action = RecommendationAction.INCLUDE
            explanation = (
                f'Scores, evidence, and {knowledge_ref_count} cold-knowledge matches support inclusion.'
                if knowledge_ref_count
                else 'Scores and evidence support inclusion.'
            )
        elif final_score < 0.40:
            action = RecommendationAction.EXCLUDE
            explanation = (
                'Knowledge-adjusted composite score is below the inclusion threshold.'
                if knowledge_ref_count
                else 'Composite score is below the inclusion threshold.'
            )
        elif knowledge_ref_count:
            explanation = (
                f'Candidate remains on watch after applying {knowledge_ref_count} cold-knowledge references.'
            )

        return ArbitrationResult(
            run_id='pending',
            symbol=candidate.symbol,
            action=action,
            final_score=round(final_score, 4),
            component_scores={key: round(value, 4) for key, value in component_scores.items()},
            risk_level=risk_level,
            risk_flags=risk_flags,
            explanation=explanation,
            evidence_refs=evidence_refs,
        )
