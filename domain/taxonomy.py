from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

TAXONOMY_VERSION = 'taxonomy-v1'


EVENT_DOMAIN_TAGS = {
    'event_domain:macro_policy',
    'event_domain:sector_rotation',
    'event_domain:company_specific',
    'event_domain:capital_flow',
    'event_domain:risk_alert',
}
EVENT_TYPE_TAGS = {
    'event_type:policy_support',
    'event_type:sector_rotation',
    'event_type:catalyst_signal',
    'event_type:fund_flow',
    'event_type:earnings_signal',
    'event_type:risk_warning',
    'event_type:liquidity_event',
}
EVENT_STRENGTH_TAGS = {
    'event_strength:weak',
    'event_strength:medium',
    'event_strength:strong',
}
EVENT_DIRECTION_TAGS = {
    'event_direction:bullish',
    'event_direction:bearish',
    'event_direction:neutral',
}
TREND_STATE_TAGS = {
    'trend_state:short_term_uptrend',
    'trend_state:short_term_downtrend',
    'trend_state:trend_neutral',
}
BREAKOUT_STATE_TAGS = {
    'breakout_state:breakout_confirmed',
    'breakout_state:breakout_attempt',
    'breakout_state:breakout_failed',
    'breakout_state:range_bound',
}
VOLUME_PATTERN_TAGS = {
    'volume_pattern:volume_expansion',
    'volume_pattern:volume_contraction',
    'volume_pattern:volume_neutral',
}
MOMENTUM_STATE_TAGS = {
    'momentum_state:momentum_hot',
    'momentum_state:momentum_balanced',
    'momentum_state:momentum_soft',
}
RISK_PATTERN_TAGS = {
    'risk_pattern:high_drawdown_risk',
    'risk_pattern:liquidity_risk',
    'risk_pattern:event_conflict_risk',
    'risk_pattern:data_quality_risk',
    'risk_pattern:consensus_risk',
    'risk_pattern:high_volatility_risk',
}
MARKET_REGIME_TAGS = {
    'market_regime:benchmark_uptrend',
    'market_regime:benchmark_downtrend',
    'market_regime:range_bound_market',
    'market_regime:high_volatility',
    'market_regime:controlled_volatility',
}
SENTIMENT_STATE_TAGS = {
    'sentiment_state:risk_on',
    'sentiment_state:risk_off',
    'sentiment_state:sentiment_mixed',
}
BREADTH_STATE_TAGS = {
    'breadth_state:breadth_strong',
    'breadth_state:breadth_weak',
    'breadth_state:breadth_mixed',
}

ALL_CANONICAL_TAGS = (
    EVENT_DOMAIN_TAGS
    | EVENT_TYPE_TAGS
    | EVENT_STRENGTH_TAGS
    | EVENT_DIRECTION_TAGS
    | TREND_STATE_TAGS
    | BREAKOUT_STATE_TAGS
    | VOLUME_PATTERN_TAGS
    | MOMENTUM_STATE_TAGS
    | RISK_PATTERN_TAGS
    | MARKET_REGIME_TAGS
    | SENTIMENT_STATE_TAGS
    | BREADTH_STATE_TAGS
)

TAG_ALIASES = {
    'rotation': 'event_type:sector_rotation',
    'sector_rotation': 'event_type:sector_rotation',
    'sector rotation': 'event_type:sector_rotation',
    '轮动': 'event_type:sector_rotation',
    'policy': 'event_domain:macro_policy',
    'macro_policy': 'event_domain:macro_policy',
    '政策': 'event_domain:macro_policy',
    'policy_support': 'event_type:policy_support',
    'policy tailwind': 'event_type:policy_support',
    '政策支持': 'event_type:policy_support',
    'catalyst': 'event_type:catalyst_signal',
    'signal': 'event_type:catalyst_signal',
    '催化': 'event_type:catalyst_signal',
    'fund_flow': 'event_type:fund_flow',
    'capital_flow': 'event_domain:capital_flow',
    '资金': 'event_domain:capital_flow',
    'inflow': 'event_type:fund_flow',
    'outflow': 'event_type:fund_flow',
    'risk_warning': 'event_type:risk_warning',
    'warning': 'event_type:risk_warning',
    '风险提示': 'event_type:risk_warning',
    'liquidity_event': 'event_type:liquidity_event',
    'liquidity': 'event_type:liquidity_event',
    'earnings': 'event_type:earnings_signal',
    '财报': 'event_type:earnings_signal',
    'bullish': 'event_direction:bullish',
    'positive': 'event_direction:bullish',
    '利好': 'event_direction:bullish',
    'bearish': 'event_direction:bearish',
    'negative': 'event_direction:bearish',
    '利空': 'event_direction:bearish',
    'neutral': 'event_direction:neutral',
    'medium': 'event_strength:medium',
    'moderate': 'event_strength:medium',
    'weak': 'event_strength:weak',
    'soft': 'event_strength:weak',
    'strong': 'event_strength:strong',
    'hot': 'event_strength:strong',
    'surge': 'event_strength:strong',
    'short_term_uptrend': 'trend_state:short_term_uptrend',
    'uptrend': 'trend_state:short_term_uptrend',
    'short_term_downtrend': 'trend_state:short_term_downtrend',
    'downtrend': 'trend_state:short_term_downtrend',
    'trend_neutral': 'trend_state:trend_neutral',
    'breakout_confirmed': 'breakout_state:breakout_confirmed',
    'breakout': 'breakout_state:breakout_confirmed',
    'breakout_attempt': 'breakout_state:breakout_attempt',
    'breakout_failed': 'breakout_state:breakout_failed',
    'range_bound': 'breakout_state:range_bound',
    'volume_expansion': 'volume_pattern:volume_expansion',
    '放量': 'volume_pattern:volume_expansion',
    'volume_contraction': 'volume_pattern:volume_contraction',
    '缩量': 'volume_pattern:volume_contraction',
    'volume_neutral': 'volume_pattern:volume_neutral',
    'momentum_hot': 'momentum_state:momentum_hot',
    'momentum_soft': 'momentum_state:momentum_soft',
    'momentum_balanced': 'momentum_state:momentum_balanced',
    'benchmark_uptrend': 'market_regime:benchmark_uptrend',
    'benchmark_downtrend': 'market_regime:benchmark_downtrend',
    'range_bound_market': 'market_regime:range_bound_market',
    'high_volatility': 'market_regime:high_volatility',
    'controlled_volatility': 'market_regime:controlled_volatility',
    'risk_on': 'sentiment_state:risk_on',
    'risk_off': 'sentiment_state:risk_off',
    'sentiment_mixed': 'sentiment_state:sentiment_mixed',
    'breadth_strong': 'breadth_state:breadth_strong',
    'breadth_weak': 'breadth_state:breadth_weak',
    'breadth_mixed': 'breadth_state:breadth_mixed',
    'high_drawdown_risk': 'risk_pattern:high_drawdown_risk',
    'liquidity_risk': 'risk_pattern:liquidity_risk',
    'event_conflict_risk': 'risk_pattern:event_conflict_risk',
    'data_quality_risk': 'risk_pattern:data_quality_risk',
    'consensus_risk': 'risk_pattern:consensus_risk',
    'high_volatility_risk': 'risk_pattern:high_volatility_risk',
}


@dataclass(slots=True)
class TagMatchResult:
    matched_tags: list[str]
    missing_required_tags: list[str]
    conflicting_tags: list[str]
    match_score: float


def normalize_tag(tag: str | None) -> str | None:
    if tag is None:
        return None
    normalized = str(tag).strip().lower().replace('-', '_')
    normalized = '_'.join(part for part in normalized.replace(':', ':').split())
    if normalized in ALL_CANONICAL_TAGS:
        return normalized
    if normalized in TAG_ALIASES:
        return TAG_ALIASES[normalized]

    if ':' not in normalized:
        for canonical in ALL_CANONICAL_TAGS:
            if canonical.endswith(f':{normalized}'):
                return canonical
    return None


def normalize_tags(tags: Iterable[str] | None) -> list[str]:
    normalized_tags = []
    for tag in tags or []:
        canonical = normalize_tag(tag)
        if canonical and canonical not in normalized_tags:
            normalized_tags.append(canonical)
    return normalized_tags


def derive_article_event_tags(article: dict) -> dict[str, list[str]]:
    text = ' '.join(
        str(article.get(key, ''))
        for key in ('title', 'summary', 'content')
    ).lower()
    raw_tags = list(article.get('raw_event_tags', []) or [])

    if 'rotation' in text or '轮动' in text:
        raw_tags.extend(['sector_rotation', 'catalyst', 'bullish'])
    if 'policy' in text or '政策' in text:
        raw_tags.extend(['macro_policy', 'policy_support'])
    if 'risk' in text or 'warning' in text or '风险' in text or '暴雷' in text:
        raw_tags.extend(['risk_warning', 'bearish'])
    if '资金' in text or 'fund' in text or 'northbound' in text or 'inflow' in text or 'outflow' in text:
        raw_tags.extend(['capital_flow', 'fund_flow'])
        raw_tags.append('bullish' if 'inflow' in text or '净流入' in text else 'bearish')

    if any(keyword in text for keyword in ('surge', '爆发', '大增', '强势')):
        raw_tags.append('strong')
    elif any(keyword in text for keyword in ('rumor', '传闻', '小幅')):
        raw_tags.append('weak')
    else:
        raw_tags.append('medium')

    if not any(normalize_tag(tag) in EVENT_DIRECTION_TAGS for tag in raw_tags):
        raw_tags.append('neutral')

    normalized_event_tags = normalize_tags(raw_tags)
    return {
        'raw_event_tags': list(dict.fromkeys(str(tag) for tag in raw_tags if tag)),
        'normalized_event_tags': normalized_event_tags,
    }


def aggregate_normalized_event_tags(articles: Iterable[dict]) -> list[str]:
    aggregated: list[str] = []
    for article in articles:
        for tag in normalize_tags(article.get('normalized_event_tags', [])):
            if tag not in aggregated:
                aggregated.append(tag)
    return aggregated


def derive_global_market_context_tags(market_snapshots: Iterable[dict]) -> dict[str, list[str]]:
    snapshots = list(market_snapshots)
    if not snapshots:
        return {
            'market_regime_tags': ['market_regime:benchmark_uptrend', 'market_regime:controlled_volatility'],
            'sentiment_state_tags': ['sentiment_state:sentiment_mixed'],
            'breadth_state_tags': ['breadth_state:breadth_mixed'],
        }

    avg_pct_chg = sum(float(item.get('pct_chg', 0.0)) for item in snapshots) / len(snapshots)
    avg_volume_ratio = sum(float(item.get('volume_ratio', 1.0)) for item in snapshots) / len(snapshots)
    avg_turnover = sum(float(item.get('turnover_rate', 0.0)) for item in snapshots) / len(snapshots)

    market_regime_tags = [
        'market_regime:benchmark_uptrend' if avg_pct_chg >= 0.3 else 'market_regime:benchmark_downtrend'
        if avg_pct_chg <= -0.3
        else 'market_regime:range_bound_market',
        'market_regime:high_volatility' if avg_volume_ratio >= 1.25 or avg_turnover >= 2.4 else 'market_regime:controlled_volatility',
    ]
    sentiment_state_tags = [
        'sentiment_state:risk_on' if avg_pct_chg >= 0.5 else 'sentiment_state:risk_off'
        if avg_pct_chg <= -0.5
        else 'sentiment_state:sentiment_mixed'
    ]
    breadth_state_tags = [
        'breadth_state:breadth_strong' if avg_pct_chg >= 0.4 and avg_volume_ratio >= 1.0 else 'breadth_state:breadth_weak'
        if avg_pct_chg <= -0.4
        else 'breadth_state:breadth_mixed'
    ]
    return {
        'market_regime_tags': normalize_tags(market_regime_tags),
        'sentiment_state_tags': normalize_tags(sentiment_state_tags),
        'breadth_state_tags': normalize_tags(breadth_state_tags),
    }


def derive_snapshot_taxonomy(
    market_snapshot: dict | None,
    indicator_snapshot: dict | None,
    global_market_context: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    market_snapshot = dict(market_snapshot or {})
    indicator_snapshot = dict(indicator_snapshot or {})
    global_market_context = global_market_context or derive_global_market_context_tags([market_snapshot])

    pct_chg = float(market_snapshot.get('pct_chg', 0.0))
    volume_ratio = float(market_snapshot.get('volume_ratio', 1.0))
    turnover_rate = float(market_snapshot.get('turnover_rate', 0.0))
    ma5_bias = float(indicator_snapshot.get('ma5_bias', 0.0))
    ma20_bias = float(indicator_snapshot.get('ma20_bias', 0.0))
    rsi14 = float(indicator_snapshot.get('rsi14', 50.0))
    macd_hist = float(indicator_snapshot.get('macd_hist', 0.0))

    trend_state = (
        'trend_state:short_term_uptrend'
        if ma5_bias >= 0.08 and ma20_bias >= 0.03
        else 'trend_state:short_term_downtrend'
        if ma5_bias <= -0.05 or ma20_bias <= -0.03
        else 'trend_state:trend_neutral'
    )
    breakout_state = (
        'breakout_state:breakout_confirmed'
        if pct_chg >= 1.2 and volume_ratio >= 1.15 and macd_hist > 0
        else 'breakout_state:breakout_failed'
        if pct_chg <= -1.0 and volume_ratio >= 1.15
        else 'breakout_state:breakout_attempt'
        if pct_chg >= 0.4
        else 'breakout_state:range_bound'
    )
    volume_pattern = (
        'volume_pattern:volume_expansion'
        if volume_ratio >= 1.15
        else 'volume_pattern:volume_contraction'
        if volume_ratio <= 0.85
        else 'volume_pattern:volume_neutral'
    )
    momentum_state = (
        'momentum_state:momentum_hot'
        if rsi14 >= 60 and macd_hist >= 0
        else 'momentum_state:momentum_soft'
        if rsi14 <= 45 or macd_hist < 0
        else 'momentum_state:momentum_balanced'
    )

    risk_pattern_tags: list[str] = []
    if volume_ratio <= 0.8 or turnover_rate <= 0.9:
        risk_pattern_tags.append('risk_pattern:liquidity_risk')
    if pct_chg <= -1.5:
        risk_pattern_tags.append('risk_pattern:high_drawdown_risk')
    if 'market_regime:high_volatility' in global_market_context.get('market_regime_tags', []):
        risk_pattern_tags.append('risk_pattern:high_volatility_risk')
    if not market_snapshot:
        risk_pattern_tags.append('risk_pattern:data_quality_risk')

    return {
        'technical_pattern_tags': normalize_tags([trend_state, breakout_state, volume_pattern, momentum_state]),
        'risk_pattern_tags': normalize_tags(risk_pattern_tags),
        'market_regime_tags': normalize_tags(global_market_context.get('market_regime_tags', [])),
        'sentiment_state_tags': normalize_tags(global_market_context.get('sentiment_state_tags', [])),
        'breadth_state_tags': normalize_tags(global_market_context.get('breadth_state_tags', [])),
    }


def match_structured_tags(
    *,
    candidate_event_tags: Iterable[str] | None,
    candidate_technical_tags: Iterable[str] | None,
    candidate_market_regime_tags: Iterable[str] | None,
    candidate_risk_tags: Iterable[str] | None,
    applicable_event_tags: Iterable[str] | None,
    applicable_technical_tags: Iterable[str] | None,
    applicable_market_regimes: Iterable[str] | None,
    negative_match_tags: Iterable[str] | None,
) -> TagMatchResult:
    candidate_tags = set(
        normalize_tags(candidate_event_tags)
        + normalize_tags(candidate_technical_tags)
        + normalize_tags(candidate_market_regime_tags)
        + normalize_tags(candidate_risk_tags)
    )
    required_tags = set(
        normalize_tags(applicable_event_tags)
        + normalize_tags(applicable_technical_tags)
        + normalize_tags(applicable_market_regimes)
    )
    negative_tags = set(normalize_tags(negative_match_tags))

    matched_tags = sorted(candidate_tags & required_tags)
    missing_required_tags = sorted(required_tags - candidate_tags)
    conflicting_tags = sorted(candidate_tags & negative_tags)

    if required_tags:
        matched_ratio = len(matched_tags) / len(required_tags)
    else:
        matched_ratio = 0.0

    conflict_penalty = (len(conflicting_tags) / max(1, len(negative_tags))) * 0.5 if negative_tags else 0.0
    match_score = round(max(0.0, min(1.0, matched_ratio - conflict_penalty)), 4)

    return TagMatchResult(
        matched_tags=matched_tags,
        missing_required_tags=missing_required_tags,
        conflicting_tags=conflicting_tags,
        match_score=match_score,
    )
