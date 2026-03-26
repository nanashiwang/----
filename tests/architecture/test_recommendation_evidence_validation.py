from __future__ import annotations

import pytest

from core.enums import RecommendationAction
from domain.schemas import CandidateOut


def test_include_recommendation_requires_evidence_refs():
    with pytest.raises(ValueError):
        CandidateOut(
            symbol='600519.SH',
            action=RecommendationAction.INCLUDE,
            final_score=0.75,
            evidence_refs=[],
        )
