from __future__ import annotations

from domain.schemas import KnowledgeItem, KnowledgePromotionResult
from memory.models import KnowledgeThresholds


class KnowledgePromotionService:
    def __init__(self, thresholds: KnowledgeThresholds | None = None):
        self.thresholds = thresholds or KnowledgeThresholds()

    def reconcile(
        self,
        repository,
        review_run_id: str,
        hot_knowledge_items: list[KnowledgeItem],
        review_report_id: str | None = None,
    ) -> KnowledgePromotionResult:
        result = KnowledgePromotionResult()
        unique_hot_items = self._unique_hot_items(hot_knowledge_items)
        active_cold_rows = repository.get_active_cold_knowledge(limit=500)
        cold_by_hot_id = {row.source_hot_knowledge_id: row for row in active_cold_rows}
        blocked_hot_ids: set[str] = set()

        for item in unique_hot_items:
            cold_row = cold_by_hot_id.get(item.knowledge_id)
            if cold_row is None:
                continue
            blocked_hot_ids.add(item.knowledge_id)

            passed = bool(
                (item.evidence_json or {}).get(
                    'last_validation_passed',
                    item.pass_count > 0 and item.pass_count >= item.fail_count,
                )
            )
            details_json = {
                'source_hot_knowledge_id': item.knowledge_id,
                'category': item.category,
                'pass_count': item.pass_count,
                'fail_count': item.fail_count,
                'pass_rate': item.pass_rate,
                'last_validation_passed': passed,
            }
            updated_cold = repository.record_cold_validation(
                cold_knowledge_id=cold_row.knowledge_id,
                passed=passed,
                source_run_id=review_run_id,
                source_review_report_id=review_report_id,
                details_json=details_json,
            )
            if updated_cold is None:
                continue

            consecutive_failures = int((updated_cold.invalid_conditions or {}).get('consecutive_failures', 0))
            if not passed and consecutive_failures >= self.thresholds.consecutive_failures:
                should_archive = consecutive_failures >= self.thresholds.consecutive_failures * 2
                demotion_reason = self._build_demotion_reason(consecutive_failures, should_archive)
                repository.demote_cold_knowledge(
                    knowledge_id=updated_cold.knowledge_id,
                    reason=demotion_reason,
                    source_run_id=review_run_id,
                    source_review_report_id=review_report_id,
                    archive=should_archive,
                )
                if should_archive:
                    result.archived_count += 1
                    result.archived_knowledge_ids.append(updated_cold.knowledge_id)
                    result.actions.append(
                        {
                            'action': 'archived',
                            'knowledge_id': updated_cold.knowledge_id,
                            'source_hot_knowledge_id': item.knowledge_id,
                            'reason': demotion_reason,
                        }
                    )
                else:
                    result.demoted_count += 1
                    result.demoted_knowledge_ids.append(updated_cold.knowledge_id)
                    result.actions.append(
                        {
                            'action': 'demoted',
                            'knowledge_id': updated_cold.knowledge_id,
                            'source_hot_knowledge_id': item.knowledge_id,
                            'reason': demotion_reason,
                        }
                    )

        promotable_rows = {
            row.knowledge_id: row
            for row in repository.list_promotable_hot_knowledge(
                min_tests=self.thresholds.tests_survived,
                min_pass_rate=self.thresholds.pass_rate,
                min_market_regimes=self.thresholds.min_market_regimes,
                limit=500,
            )
        }
        for item in unique_hot_items:
            if item.knowledge_id in blocked_hot_ids:
                continue
            if item.knowledge_id not in promotable_rows:
                continue
            hot_row = promotable_rows[item.knowledge_id]
            promotion_reason = self._build_promotion_reason(hot_row.tests_survived, hot_row.pass_rate, hot_row.evidence_json)
            cold_row = repository.promote_to_cold(
                knowledge_id=hot_row.knowledge_id,
                promotion_reason=promotion_reason,
                promotion_run_id=review_run_id,
                source_review_report_id=review_report_id,
            )
            if cold_row is None:
                continue
            result.promoted_count += 1
            result.promoted_knowledge_ids.append(cold_row.knowledge_id)
            result.actions.append(
                {
                    'action': 'promoted',
                    'knowledge_id': cold_row.knowledge_id,
                    'source_hot_knowledge_id': hot_row.knowledge_id,
                    'reason': promotion_reason,
                    'market_regimes': list(cold_row.applicable_market_regimes or []),
                }
            )

        return result

    @staticmethod
    def _unique_hot_items(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
        unique_map: dict[str, KnowledgeItem] = {}
        for item in items:
            unique_map[item.knowledge_id] = item
        return list(unique_map.values())

    @staticmethod
    def _build_promotion_reason(tests_survived: int, pass_rate: float, evidence_json: dict | None) -> str:
        market_regimes = list((evidence_json or {}).get('market_regimes', []))
        return (
            f'Promoted after {tests_survived} validations with pass rate {pass_rate:.2%}, '
            f'covering {len(market_regimes)} market regimes.'
        )

    @staticmethod
    def _build_demotion_reason(consecutive_failures: int, should_archive: bool) -> str:
        if should_archive:
            return (
                f'Archived after {consecutive_failures} consecutive failures in the rolling review window.'
            )
        return (
            f'Demoted after {consecutive_failures} consecutive failures in the rolling review window.'
        )
