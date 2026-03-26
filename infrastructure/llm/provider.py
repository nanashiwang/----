from __future__ import annotations

from typing import Any


class LLMProvider:
    def summarize_daily_brief(self, articles: list[dict[str, Any]], history: list[dict[str, Any]]) -> str:
        titles = [article.get('title', '') for article in articles[:5] if article.get('title')]
        history_hint = f' History samples: {len(history)}.' if history else ''
        if not titles:
            return 'No meaningful article was found for the requested trading day.'
        return 'Daily brief: ' + ' | '.join(titles) + history_hint

    def build_argument(self, role: str, symbol: str, context: dict[str, Any]) -> dict[str, Any]:
        base_score = float(context.get('base_score', 0.5))
        offset = {
            'bull_case_agent': 0.15,
            'bear_case_agent': -0.10,
            'technical_analyst_agent': 0.05,
            'moderator_agent': 0.0,
        }.get(role, 0.0)
        return {
            'role': role,
            'symbol': symbol,
            'score': max(0.0, min(1.0, base_score + offset)),
            'summary': f'{role} generated a placeholder view for {symbol}.',
        }
