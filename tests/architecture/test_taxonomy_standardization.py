from __future__ import annotations

from domain.taxonomy import (
    derive_article_event_tags,
    derive_snapshot_taxonomy,
    match_structured_tags,
)


def test_event_aliases_are_normalized():
    article = {
        'title': 'Sector rotation signal turns bullish',
        'summary': 'Policy support adds a strong catalyst for the sector.',
        'content': 'Rotation and policy tailwind keep sentiment positive.',
        'raw_event_tags': ['rotation', 'policy_support', 'bullish'],
    }

    payload = derive_article_event_tags(article)

    assert 'event_type:sector_rotation' in payload['normalized_event_tags']
    assert 'event_type:policy_support' in payload['normalized_event_tags']
    assert 'event_direction:bullish' in payload['normalized_event_tags']


def test_snapshot_taxonomy_outputs_standard_technical_tags():
    market_snapshot = {
        'pct_chg': 1.8,
        'turnover_rate': 2.6,
        'volume_ratio': 1.35,
    }
    indicator_snapshot = {
        'ma5_bias': 0.12,
        'ma20_bias': 0.06,
        'rsi14': 67,
        'macd_hist': 0.08,
    }

    payload = derive_snapshot_taxonomy(
        market_snapshot,
        indicator_snapshot,
        {
            'market_regime_tags': ['market_regime:benchmark_uptrend', 'market_regime:high_volatility'],
            'sentiment_state_tags': ['sentiment_state:risk_on'],
            'breadth_state_tags': ['breadth_state:breadth_strong'],
        },
    )

    assert 'trend_state:short_term_uptrend' in payload['technical_pattern_tags']
    assert 'breakout_state:breakout_confirmed' in payload['technical_pattern_tags']
    assert 'momentum_state:momentum_hot' in payload['technical_pattern_tags']
    assert 'risk_pattern:high_volatility_risk' in payload['risk_pattern_tags']


def test_structured_tag_match_returns_conflicts_and_missing_tags():
    result = match_structured_tags(
        candidate_event_tags=['sector_rotation', 'bullish'],
        candidate_technical_tags=['short_term_uptrend', 'momentum_balanced'],
        candidate_market_regime_tags=['benchmark_uptrend', 'controlled_volatility'],
        candidate_risk_tags=['momentum_balanced'],
        applicable_event_tags=['event_type:sector_rotation', 'event_direction:bullish'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend', 'market_regime:controlled_volatility'],
        negative_match_tags=['momentum_balanced', 'high_volatility_risk'],
    )

    assert 'event_type:sector_rotation' in result.matched_tags
    assert result.missing_required_tags == []
    assert 'momentum_state:momentum_balanced' in result.conflicting_tags
    assert result.match_score >= 0


def test_structured_tag_match_handles_empty_inputs():
    result = match_structured_tags(
        candidate_event_tags=[],
        candidate_technical_tags=[],
        candidate_market_regime_tags=[],
        candidate_risk_tags=[],
        applicable_event_tags=[],
        applicable_technical_tags=[],
        applicable_market_regimes=[],
        negative_match_tags=[],
    )

    assert result.matched_tags == []
    assert result.conflicting_tags == []
    assert result.match_score == 0.0
